import streamlit as st
from supabase import create_client
from datetime import datetime, date
from groq import Groq
import json

# Page config
st.set_page_config(page_title="Committees", page_icon="📋", layout="wide")

# Hide sidebar
st.markdown("""
    <style>
    [data-testid="stSidebar"] {display: none;}
    </style>
""", unsafe_allow_html=True)

# Initialize Supabase
supabase = create_client(
    st.secrets["supabase"]["url"],
    st.secrets["supabase"]["key"]
)

# Initialize Groq
@st.cache_resource
def get_groq():
    return Groq(api_key=st.secrets["GROQ_API_KEY"])

groq_client = get_groq()

# Initialize session state
if 'committee_view' not in st.session_state:
    st.session_state.committee_view = 'home'
if 'selected_committee' not in st.session_state:
    st.session_state.selected_committee = None
if 'selected_meeting' not in st.session_state:
    st.session_state.selected_meeting = None

# Navigation handler
def navigate_to(view, committee=None, meeting=None):
    st.session_state.committee_view = view
    if committee:
        st.session_state.selected_committee = committee
    if meeting:
        st.session_state.selected_meeting = meeting
    st.rerun()

# Committee configurations
COMMITTEES = {
    'finance': {
        'name': 'Finance Committee',
        'icon': '💰',
        'color': '#059669',
        'description': 'Budget · Expenditure · Reports'
    },
    'whs': {
        'name': 'WHS Committee',
        'icon': '🦺',
        'color': '#ea580c',
        'description': 'Safety · Hazards · Compliance'
    },
    'social': {
        'name': 'Social Club',
        'icon': '🎉',
        'color': '#7c3aed',
        'description': 'Events · Activities · Fun'
    },
    'special': {
        'name': 'Special Events',
        'icon': '✨',
        'color': '#ec4899',
        'description': 'Planning · Coordination · Celebration'
    }
}

# ============================================================================
# COMMITTEE MEMBERS DATABASE FUNCTIONS
# ============================================================================

def get_all_committee_roles():
    """Get all committees with their members"""
    try:
        # Get committees
        committees_response = supabase.table('committee_roles')\
            .select('*')\
            .order('display_order', desc=False)\
            .execute()
        
        committees = committees_response.data if committees_response.data else []
        
        # Get members for each committee
        for committee in committees:
            members_response = supabase.table('committee_role_members')\
                .select('*')\
                .eq('committee_id', committee['id'])\
                .order('display_order', desc=False)\
                .execute()
            
            committee['members'] = members_response.data if members_response.data else []
        
        return committees
    except Exception as e:
        return []

def add_committee_role(name, description=""):
    """Add a new committee role"""
    try:
        response = supabase.table('committee_roles')\
            .select('display_order')\
            .order('display_order', desc=True)\
            .limit(1)\
            .execute()
        
        max_order = response.data[0]['display_order'] if response.data else 0
        
        result = supabase.table('committee_roles').insert({
            'name': name,
            'description': description,
            'display_order': max_order + 1
        }).execute()
        
        return result.data[0] if result.data else None
    except Exception as e:
        st.error(f"Error adding committee: {str(e)}")
        return None

def update_committee_role(committee_id, name=None, description=None):
    """Update committee details"""
    try:
        updates = {'updated_at': 'NOW()'}
        if name:
            updates['name'] = name
        if description is not None:
            updates['description'] = description
        
        supabase.table('committee_roles')\
            .update(updates)\
            .eq('id', committee_id)\
            .execute()
        
        return True
    except Exception as e:
        st.error(f"Error updating committee: {str(e)}")
        return False

def delete_committee_role(committee_id):
    """Delete a committee (cascade deletes members)"""
    try:
        supabase.table('committee_roles').delete().eq('id', committee_id).execute()
        return True
    except Exception as e:
        st.error(f"Error deleting committee: {str(e)}")
        return False

def add_committee_role_member(committee_id, staff_name, role=""):
    """Add a member to a committee"""
    try:
        response = supabase.table('committee_role_members')\
            .select('display_order')\
            .eq('committee_id', committee_id)\
            .order('display_order', desc=True)\
            .limit(1)\
            .execute()
        
        max_order = response.data[0]['display_order'] if response.data else 0
        
        supabase.table('committee_role_members').insert({
            'committee_id': committee_id,
            'staff_name': staff_name,
            'role': role,
            'display_order': max_order + 1
        }).execute()
        
        return True
    except Exception as e:
        st.error(f"Error adding member: {str(e)}")
        return False

def update_committee_role_member(member_id, staff_name=None, role=None):
    """Update a committee member"""
    try:
        updates = {}
        if staff_name:
            updates['staff_name'] = staff_name
        if role is not None:
            updates['role'] = role
        
        supabase.table('committee_role_members')\
            .update(updates)\
            .eq('id', member_id)\
            .execute()
        
        return True
    except Exception as e:
        st.error(f"Error updating member: {str(e)}")
        return False

def delete_committee_role_member(member_id):
    """Remove a member from a committee"""
    try:
        supabase.table('committee_role_members').delete().eq('id', member_id).execute()
        return True
    except Exception as e:
        st.error(f"Error removing member: {str(e)}")
        return False

def initialize_default_committee_roles():
    """Initialize the default committees from Candice's data"""
    default_committees = [
        {
            'name': 'PAC',
            'description': 'Partnership & Cooperation Committee',
            'members': [
                ('Candice', 'Leader'),
                ('Naomi', 'SSO rep'),
                ('Ben', 'AEU Rep'),
                ('Brenton', 'Teacher Rep')
            ]
        },
        {
            'name': 'WHS',
            'description': 'Work Health & Safety',
            'members': [
                ('Candice', 'OHS Rep'),
                ('Naomi', ''),
                ('Ben Selga', ''),
                ('Caitie', ''),
                ('Roisin', '')
            ]
        },
        {
            'name': 'Social Club',
            'description': '',
            'members': [
                ('Ben Sutton', ''),
                ('Vinnie', ''),
                ('Jacqui', ''),
                ('Annette', '')
            ]
        },
        {
            'name': 'Centre Spec Events',
            'description': 'Centre Special Events',
            'members': [
                ('Brenton', ''),
                ('Ben Selga', ''),
                ('Annette', '')
            ]
        },
        {
            'name': 'Leaving Gift',
            'description': '',
            'members': [
                ('Caitie', ''),
                ('Jacqui', ''),
                ('Annette', ''),
                ('Candice', ''),
                ('Naomi', '')
            ]
        },
        {
            'name': 'OHS',
            'description': 'Occupational Health & Safety',
            'members': [
                ('Roisin', 'Proxy'),
                ('Caitie', 'Proxy')
            ]
        },
        {
            'name': 'AEU',
            'description': 'Australian Education Union',
            'members': [
                ('Roisin', 'Proxy'),
                ('Ben Sutton', 'Proxy')
            ]
        },
        {
            'name': 'Fire Warden',
            'description': '',
            'members': [
                ('Brenton', ''),
                ('Ben Selga', '')
            ]
        },
        {
            'name': 'First Aid Officer',
            'description': '',
            'members': [
                ('Naomi', '')
            ]
        },
        {
            'name': '3P Learning Coordinator',
            'description': '',
            'members': [
                ('Caitie', '')
            ]
        }
    ]
    
    try:
        for idx, committee_data in enumerate(default_committees):
            committee = supabase.table('committee_roles').insert({
                'name': committee_data['name'],
                'description': committee_data['description'],
                'display_order': idx
            }).execute()
            
            if committee.data:
                committee_id = committee.data[0]['id']
                
                for member_idx, (staff_name, role) in enumerate(committee_data['members']):
                    supabase.table('committee_role_members').insert({
                        'committee_id': committee_id,
                        'staff_name': staff_name,
                        'role': role,
                        'display_order': member_idx
                    }).execute()
        
        st.success("✅ Default committee roles initialized successfully!")
        return True
    except Exception as e:
        st.error(f"Error initializing committees: {str(e)}")
        return False

def display_committee_member_card(committee, edit_mode=False):
    """Display a committee member card"""
    with st.container():
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.markdown(f"### 🤝 {committee['name']}")
            if committee.get('description'):
                st.caption(committee['description'])
        
        with col2:
            if edit_mode:
                if st.button("✏️", key=f"edit_{committee['id']}", help="Edit committee", use_container_width=True):
                    st.session_state[f'editing_{committee["id"]}'] = True
                    st.rerun()
        
        # Display members
        if committee['members']:
            member_display = []
            for member in committee['members']:
                if member['role']:
                    member_display.append(f"**{member['staff_name']}** ({member['role']})")
                else:
                    member_display.append(f"**{member['staff_name']}**")
            
            st.markdown("**Members:** " + " • ".join(member_display))
        else:
            st.caption("_No members assigned_")
        
        st.divider()

def edit_committee_member_form(committee):
    """Show edit form for a committee"""
    with st.container():
        st.markdown(f"### ✏️ Editing: {committee['name']}")
        
        # Edit committee details
        with st.form(key=f"edit_committee_{committee['id']}"):
            new_name = st.text_input("Committee Name", value=committee['name'])
            new_description = st.text_area("Description", value=committee.get('description', ''))
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 Save Changes", use_container_width=True):
                    if update_committee_role(committee['id'], new_name, new_description):
                        st.success("✅ Committee updated!")
                        st.session_state.pop(f'editing_{committee["id"]}', None)
                        st.rerun()
            with col2:
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    st.session_state.pop(f'editing_{committee["id"]}', None)
                    st.rerun()
        
        st.divider()
        
        # Edit members
        st.markdown("#### Members")
        
        for member in committee['members']:
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            
            with col1:
                new_staff_name = st.text_input(
                    "Staff Name",
                    value=member['staff_name'],
                    key=f"member_name_{member['id']}",
                    label_visibility="collapsed"
                )
            
            with col2:
                new_role = st.text_input(
                    "Role",
                    value=member.get('role', ''),
                    key=f"member_role_{member['id']}",
                    label_visibility="collapsed"
                )
            
            with col3:
                if st.button("💾", key=f"save_member_{member['id']}", help="Save changes"):
                    if update_committee_role_member(member['id'], new_staff_name, new_role):
                        st.success("✅ Updated!")
                        st.rerun()
            
            with col4:
                if st.button("🗑️", key=f"delete_member_{member['id']}", help="Remove member"):
                    if delete_committee_role_member(member['id']):
                        st.success("✅ Removed!")
                        st.rerun()
        
        # Add new member form
        st.markdown("#### Add New Member")
        with st.form(key=f"add_member_{committee['id']}"):
            col1, col2, col3 = st.columns([3, 2, 2])
            
            with col1:
                add_staff_name = st.text_input("Staff Name")
            with col2:
                add_role = st.text_input("Role (optional)")
            with col3:
                st.write("")
                if st.form_submit_button("➕ Add Member", use_container_width=True):
                    if add_staff_name:
                        if add_committee_role_member(committee['id'], add_staff_name, add_role):
                            st.success(f"✅ Added {add_staff_name}")
                            st.rerun()
                    else:
                        st.error("Please enter a staff name")
        
        # Delete committee option
        st.divider()
        with st.expander("🗑️ Delete This Committee"):
            st.warning("⚠️ This will permanently delete the committee and all its members.")
            if st.button("🗑️ Delete Committee", type="secondary"):
                if delete_committee_role(committee['id']):
                    st.success("✅ Committee deleted!")
                    st.session_state.pop(f'editing_{committee["id"]}', None)
                    st.rerun()
        
        st.divider()

# ========== HEADER ==========
st.markdown("""
    <div style="background: linear-gradient(135deg, #1e3a5f 0%, #2d5a8c 100%); 
                padding: 2rem; border-radius: 12px; margin-bottom: 2rem; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <div style="display: flex; align-items: center; gap: 1rem;">
            <div style="font-size: 3rem;">🏛️</div>
            <div>
                <h1 style="margin: 0; color: white; font-size: 2.2rem;">Committees</h1>
                <p style="margin: 0; color: #e0e7ff; font-size: 1rem;">Cowandilla Learning Centre</p>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# ========== HOME VIEW ==========
if st.session_state.committee_view == 'home':
    
    st.markdown("<h3 style='color: #1e3a5f; margin-bottom: 1.5rem;'>Select a committee to manage meetings and documents.</h3>", unsafe_allow_html=True)
    
    # Committee Cards
    col1, col2 = st.columns(2)
    
    with col1:
        # Finance Card
        st.markdown(f"""
            <div style="border: 3px solid {COMMITTEES['finance']['color']}; border-radius: 16px; padding: 2rem; 
                        background: white; margin-bottom: 1.5rem; min-height: 220px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="font-size: 3.5rem; margin-bottom: 1rem;">{COMMITTEES['finance']['icon']}</div>
                <h3 style="color: #1e3a5f; margin-bottom: 0.5rem;">{COMMITTEES['finance']['name']}</h3>
                <p style="color: #64748b; margin-bottom: 1rem;">{COMMITTEES['finance']['description']}</p>
                <span style="background: #d1fae5; color: #065f46; padding: 0.4rem 0.8rem; 
                            border-radius: 20px; font-size: 0.85rem; font-weight: 600;">● Active</span>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Open Finance", key="btn_finance", use_container_width=True):
            navigate_to('committee_home', 'finance')
        
        # Social Club Card
        st.markdown(f"""
            <div style="border: 3px solid {COMMITTEES['social']['color']}; border-radius: 16px; padding: 2rem; 
                        background: white; margin-bottom: 1.5rem; min-height: 220px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="font-size: 3.5rem; margin-bottom: 1rem;">{COMMITTEES['social']['icon']}</div>
                <h3 style="color: #1e3a5f; margin-bottom: 0.5rem;">{COMMITTEES['social']['name']}</h3>
                <p style="color: #64748b; margin-bottom: 1rem;">{COMMITTEES['social']['description']}</p>
                <span style="background: #e9d5ff; color: #6b21a8; padding: 0.4rem 0.8rem; 
                            border-radius: 20px; font-size: 0.85rem; font-weight: 600;">● Active</span>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Open Social Club", key="btn_social", use_container_width=True):
            navigate_to('committee_home', 'social')
    
    with col2:
        # WHS Card
        st.markdown(f"""
            <div style="border: 3px solid {COMMITTEES['whs']['color']}; border-radius: 16px; padding: 2rem; 
                        background: white; margin-bottom: 1.5rem; min-height: 220px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="font-size: 3.5rem; margin-bottom: 1rem;">{COMMITTEES['whs']['icon']}</div>
                <h3 style="color: #1e3a5f; margin-bottom: 0.5rem;">{COMMITTEES['whs']['name']}</h3>
                <p style="color: #64748b; margin-bottom: 1rem;">{COMMITTEES['whs']['description']}</p>
                <span style="background: #fef3c7; color: #92400e; padding: 0.4rem 0.8rem; 
                            border-radius: 20px; font-size: 0.85rem; font-weight: 600;">● Active</span>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Open WHS", key="btn_whs", use_container_width=True):
            navigate_to('committee_home', 'whs')
        
        # Special Events Card
        st.markdown(f"""
            <div style="border: 3px solid {COMMITTEES['special']['color']}; border-radius: 16px; padding: 2rem; 
                        background: white; margin-bottom: 1.5rem; min-height: 220px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="font-size: 3.5rem; margin-bottom: 1rem;">{COMMITTEES['special']['icon']}</div>
                <h3 style="color: #1e3a5f; margin-bottom: 0.5rem;">{COMMITTEES['special']['name']}</h3>
                <p style="color: #64748b; margin-bottom: 1rem;">{COMMITTEES['special']['description']}</p>
                <span style="background: #fce7f3; color: #9f1239; padding: 0.4rem 0.8rem; 
                            border-radius: 20px; font-size: 0.85rem; font-weight: 600;">● Active</span>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Open Special Events", key="btn_special", use_container_width=True):
            navigate_to('committee_home', 'special')
    
    # Additional Cards - Below
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        # Documents Card
        st.markdown("""
            <div style="border: 3px solid #0891b2; border-radius: 16px; padding: 2rem; 
                        background: white; margin-bottom: 1.5rem; min-height: 220px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="font-size: 3.5rem; margin-bottom: 1rem;">📄</div>
                <h3 style="color: #1e3a5f; margin-bottom: 0.5rem;">Documents Library</h3>
                <p style="color: #64748b; margin-bottom: 1rem;">Policies · Procedures · Resources</p>
                <span style="background: #cffafe; color: #0e7490; padding: 0.4rem 0.8rem; 
                            border-radius: 20px; font-size: 0.85rem; font-weight: 600;">● Active</span>
            </div>
        """, unsafe_allow_html=True)
        if st.button("View Documents", key="btn_documents", use_container_width=True):
            navigate_to('documents')
    
    with col2:
        # Committee Members Card (NEW!)
        st.markdown("""
            <div style="border: 3px solid #8b5cf6; border-radius: 16px; padding: 2rem; 
                        background: white; margin-bottom: 1.5rem; min-height: 220px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="font-size: 3.5rem; margin-bottom: 1rem;">👥</div>
                <h3 style="color: #1e3a5f; margin-bottom: 0.5rem;">Committee Members</h3>
                <p style="color: #64748b; margin-bottom: 1rem;">Roles · Positions · Staff</p>
                <span style="background: #ede9fe; color: #6b21a8; padding: 0.4rem 0.8rem; 
                            border-radius: 20px; font-size: 0.85rem; font-weight: 600;">● Active</span>
            </div>
        """, unsafe_allow_html=True)
        if st.button("View Members", key="btn_members", use_container_width=True):
            navigate_to('members')

# ========== COMMITTEE HOME VIEW ==========
elif st.session_state.committee_view == 'committee_home':
    
    committee_key = st.session_state.selected_committee
    committee = COMMITTEES.get(committee_key, {})
    
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, {committee['color']}15 0%, {committee['color']}30 100%); 
                    padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem; 
                    border-left: 5px solid {committee['color']};">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div style="font-size: 2.5rem;">{committee['icon']}</div>
                <div>
                    <h2 style="margin: 0; color: #1e3a5f;">{committee['name']}</h2>
                    <p style="margin: 0; color: #64748b;">{committee['description']}</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📅 Schedule Meeting", use_container_width=True):
            navigate_to('schedule_meeting', committee_key)
    
    with col2:
        if st.button("📋 View All Meetings", use_container_width=True):
            navigate_to('view_meetings', committee_key)
    
    with col3:
        if st.button("↩ Back", use_container_width=True):
            navigate_to('home')
    
    st.divider()
    
    # Display upcoming meetings
    try:
        response = supabase.table("committees_meetings")\
            .select("*")\
            .eq("committee_name", committee_key)\
            .gte("meeting_date", date.today().isoformat())\
            .order("meeting_date", desc=False)\
            .limit(3)\
            .execute()
        
        if response.data:
            st.subheader("📅 Upcoming Meetings")
            for meeting in response.data:
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.markdown(f"**{meeting['meeting_title']}**")
                        st.caption(f"📍 {meeting.get('location', 'TBA')}")
                    
                    with col2:
                        st.caption(f"📅 {meeting['meeting_date']}")
                        st.caption(f"🕐 {meeting['meeting_time']}")
                    
                    with col3:
                        if st.button("View", key=f"view_{meeting['id']}", use_container_width=True):
                            navigate_to('meeting_detail', committee_key, meeting['id'])
                    
                    st.divider()
        else:
            st.info("No upcoming meetings scheduled.")
    
    except Exception as e:
        st.error(f"Error loading meetings: {str(e)}")
    
    # Display recent minutes
    try:
        response = supabase.table("committees_meetings")\
            .select("*")\
            .eq("committee_name", committee_key)\
            .lt("meeting_date", date.today().isoformat())\
            .order("meeting_date", desc=True)\
            .limit(3)\
            .execute()
        
        if response.data:
            st.subheader("📝 Recent Minutes")
            for meeting in response.data:
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.markdown(f"**{meeting['meeting_title']}**")
                        has_minutes = "✅" if meeting.get('minutes_generated') else "⏳"
                        st.caption(f"{has_minutes} Minutes")
                    
                    with col2:
                        st.caption(f"📅 {meeting['meeting_date']}")
                    
                    with col3:
                        if st.button("View", key=f"recent_{meeting['id']}", use_container_width=True):
                            navigate_to('meeting_detail', committee_key, meeting['id'])
                    
                    st.divider()
    
    except Exception as e:
        st.error(f"Error loading recent meetings: {str(e)}")

# ========== SCHEDULE MEETING VIEW ==========
elif st.session_state.committee_view == 'schedule_meeting':
    
    committee_key = st.session_state.selected_committee
    committee = COMMITTEES.get(committee_key, {})
    
    st.markdown(f"### {committee['icon']} Schedule {committee['name']} Meeting")
    
    with st.form("schedule_meeting_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            meeting_title = st.text_input("Meeting Title*", placeholder="e.g., Q2 2026 Review")
            meeting_date = st.date_input("Meeting Date*", value=datetime.now().date())
            meeting_time = st.time_input("Meeting Time*", value=datetime.now().time())
        
        with col2:
            location = st.text_input("Location", placeholder="e.g., Staff Room, Teams Meeting")
            attendees = st.text_area("Expected Attendees", placeholder="List expected attendees...")
        
        agenda_items = st.text_area(
            "Agenda Items (one per line)",
            placeholder="Welcome and introductions\nReview of previous minutes\nBudget discussion\nAny other business",
            height=150
        )
        
        notes = st.text_area("Additional Notes (optional)", placeholder="Any additional information...")
        
        col1, col2 = st.columns(2)
        
        with col1:
            submit = st.form_submit_button("📅 Schedule Meeting", use_container_width=True)
        
        with col2:
            cancel = st.form_submit_button("❌ Cancel", use_container_width=True)
        
        if cancel:
            navigate_to('committee_home', committee_key)
        
        if submit:
            if not meeting_title or not meeting_date or not meeting_time:
                st.error("Please complete all required fields.")
            else:
                try:
                    supabase.table("committees_meetings").insert({
                        "committee_name": committee_key,
                        "meeting_title": meeting_title,
                        "meeting_date": meeting_date.isoformat(),
                        "meeting_time": meeting_time.strftime("%H:%M"),
                        "location": location,
                        "attendees": attendees,
                        "agenda_items": agenda_items,
                        "notes": notes,
                        "created_at": datetime.now().isoformat()
                    }).execute()
                    
                    st.success("✅ Meeting scheduled successfully!")
                    st.balloons()
                    st.info("Returning to committee home...")
                    navigate_to('committee_home', committee_key)
                
                except Exception as e:
                    st.error(f"Error scheduling meeting: {str(e)}")

# ========== VIEW MEETINGS LIST ==========
elif st.session_state.committee_view == 'view_meetings':
    
    committee_key = st.session_state.selected_committee
    committee = COMMITTEES.get(committee_key, {})
    
    st.markdown(f"### {committee['icon']} All {committee['name']} Meetings")
    
    if st.button("↩ Back to Committee", use_container_width=True):
        navigate_to('committee_home', committee_key)
    
    st.divider()
    
    # Tabs for upcoming and past
    tab1, tab2 = st.tabs(["📅 Upcoming", "📝 Past Meetings"])
    
    with tab1:
        try:
            response = supabase.table("committees_meetings")\
                .select("*")\
                .eq("committee_name", committee_key)\
                .gte("meeting_date", date.today().isoformat())\
                .order("meeting_date", desc=False)\
                .execute()
            
            if response.data:
                for meeting in response.data:
                    with st.container():
                        col1, col2, col3 = st.columns([3, 2, 1])
                        
                        with col1:
                            st.markdown(f"**{meeting['meeting_title']}**")
                            st.caption(f"📍 {meeting.get('location', 'TBA')}")
                        
                        with col2:
                            st.caption(f"📅 {meeting['meeting_date']}")
                            st.caption(f"🕐 {meeting['meeting_time']}")
                        
                        with col3:
                            if st.button("View", key=f"upcoming_{meeting['id']}", use_container_width=True):
                                navigate_to('meeting_detail', committee_key, meeting['id'])
                        
                        st.divider()
            else:
                st.info("No upcoming meetings scheduled.")
        
        except Exception as e:
            st.error(f"Error loading meetings: {str(e)}")
    
    with tab2:
        try:
            response = supabase.table("committees_meetings")\
                .select("*")\
                .eq("committee_name", committee_key)\
                .lt("meeting_date", date.today().isoformat())\
                .order("meeting_date", desc=True)\
                .execute()
            
            if response.data:
                for meeting in response.data:
                    with st.container():
                        col1, col2, col3 = st.columns([3, 2, 1])
                        
                        with col1:
                            st.markdown(f"**{meeting['meeting_title']}**")
                            has_minutes = "✅" if meeting.get('minutes_generated') else "⏳"
                            st.caption(f"{has_minutes} Minutes")
                        
                        with col2:
                            st.caption(f"📅 {meeting['meeting_date']}")
                        
                        with col3:
                            if st.button("View", key=f"past_{meeting['id']}", use_container_width=True):
                                navigate_to('meeting_detail', committee_key, meeting['id'])
                        
                        st.divider()
            else:
                st.info("No past meetings found.")
        
        except Exception as e:
            st.error(f"Error loading meetings: {str(e)}")

# ========== MEETING DETAIL VIEW ==========
elif st.session_state.committee_view == 'meeting_detail':
    
    try:
        meeting_id = st.session_state.selected_meeting
        committee_key = st.session_state.selected_committee
        committee = COMMITTEES.get(committee_key, {})
        
        response = supabase.table("committees_meetings")\
            .select("*")\
            .eq("id", meeting_id)\
            .single()\
            .execute()
        
        if not response.data:
            st.error("Meeting not found.")
            if st.button("↩ Return"):
                navigate_to('committee_home', committee_key)
        else:
            meeting = response.data
            
            # Meeting header
            st.markdown(f"""
                <div style="background: linear-gradient(135deg, {committee['color']}15 0%, {committee['color']}30 100%); 
                            padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem; 
                            border-left: 5px solid {committee['color']};">
                    <h2 style="margin: 0; color: #1e3a5f;">{committee['icon']} {meeting['meeting_title']}</h2>
                    <p style="margin: 0.5rem 0 0 0; color: #64748b;">
                        📅 {meeting['meeting_date']} • 🕐 {meeting['meeting_time']} • 📍 {meeting.get('location', 'TBA')}
                    </p>
                </div>
            """, unsafe_allow_html=True)
            
            # Action tabs
            tab1, tab2, tab3 = st.tabs(["📋 Meeting Details", "🤖 Generate Minutes (AI)", "✏️ Enter Minutes Manually"])
            
            with tab1:
                st.subheader("Meeting Information")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**📅 Date:** {meeting['meeting_date']}")
                    st.markdown(f"**🕐 Time:** {meeting['meeting_time']}")
                    st.markdown(f"**📍 Location:** {meeting.get('location', 'TBA')}")
                
                with col2:
                    if meeting.get('attendees'):
                        st.markdown("**👥 Expected Attendees:**")
                        st.caption(meeting['attendees'])
                
                if meeting.get('agenda_items'):
                    st.markdown("**📋 Agenda:**")
                    agenda_lines = meeting['agenda_items'].split('\n')
                    for i, item in enumerate(agenda_lines, 1):
                        if item.strip():
                            st.markdown(f"{i}. {item.strip()}")
                
                if meeting.get('notes'):
                    st.markdown("**📝 Notes:**")
                    st.info(meeting['notes'])
            
            with tab2:
                st.subheader("🤖 AI-Assisted Minutes Generation")
                st.markdown("""
                    Upload a transcript or paste discussion notes, and AI will generate professionally formatted minutes 
                    following DfE committee minutes format.
                """)
                
                input_method = st.radio(
                    "Input Method:",
                    ["📝 Paste Text", "📎 Upload File"],
                    horizontal=True
                )
                
                transcript_text = ""
                
                if input_method == "📝 Paste Text":
                    transcript_text = st.text_area(
                        "Paste transcript or notes here:",
                        height=300,
                        placeholder="Paste your meeting transcript, notes, or recording transcription here..."
                    )
                else:
                    uploaded_file = st.file_uploader("Upload transcript file", type=['txt', 'docx', 'pdf'])
                    if uploaded_file:
                        transcript_text = uploaded_file.read().decode('utf-8')
                        st.success(f"✅ Loaded: {uploaded_file.name}")
                
                if st.button("🤖 Generate Minutes with AI", use_container_width=True, type="primary"):
                    if not transcript_text:
                        st.error("Please provide transcript text or upload a file.")
                    else:
                        with st.spinner("🤖 AI is generating your minutes..."):
                            try:
                                # Build prompt for minutes generation
                                prompt = f"""You are a professional committee secretary. Generate formal committee meeting minutes following Department for Education (DfE) format.

Meeting Details:
- Committee: {committee['name']}
- Title: {meeting['meeting_title']}
- Date: {meeting['meeting_date']}
- Time: {meeting['meeting_time']}
- Location: {meeting.get('location', 'Not specified')}

Agenda:
{meeting.get('agenda_items', 'Not specified')}

Transcript/Notes:
{transcript_text}

Generate comprehensive meeting minutes that include:
1. Meeting header with all details
2. Attendees (present and apologies)
3. Minutes for each agenda item with:
   - Discussion summary
   - Decisions made
   - Action items (with responsible person and deadline if mentioned)
4. Next meeting date/details (if mentioned)

Format professionally and clearly. Use clear headings and bullet points where appropriate."""

                                # Call Groq API
                                response = groq_client.chat.completions.create(
                                    model="llama-3.3-70b-versatile",
                                    messages=[
                                        {"role": "system", "content": "You are a professional committee secretary specializing in DfE-format minutes."},
                                        {"role": "user", "content": prompt}
                                    ],
                                    temperature=0.3,
                                    max_tokens=4000
                                )
                                
                                generated_minutes = response.choices[0].message.content
                                
                                # Save to database
                                supabase.table("committees_meetings")\
                                    .update({
                                        "minutes_generated": True,
                                        "minutes_text": generated_minutes,
                                        "transcript": transcript_text,
                                        "minutes_generated_at": datetime.now().isoformat()
                                    })\
                                    .eq("id", meeting_id)\
                                    .execute()
                                
                                st.success("✅ Minutes generated successfully!")
                                st.balloons()
                                
                                st.markdown("### Generated Minutes")
                                st.markdown(generated_minutes)
                                
                                st.download_button(
                                    label="📥 Download Minutes",
                                    data=generated_minutes,
                                    file_name=f"{meeting['meeting_title']}_{meeting['meeting_date']}_Minutes.txt",
                                    mime="text/plain",
                                    use_container_width=True
                                )
                            
                            except Exception as e:
                                st.error(f"Error generating minutes: {str(e)}")
            
            with tab3:
                st.subheader("✏️ Enter Minutes Manually")
                
                with st.form("manual_minutes"):
                    manual_minutes = st.text_area(
                        "Enter meeting minutes:",
                        value=meeting.get('minutes_text', ''),
                        height=400,
                        placeholder="Type or paste your minutes here..."
                    )
                    
                    if st.form_submit_button("💾 Save Minutes", use_container_width=True):
                        try:
                            supabase.table("committees_meetings")\
                                .update({
                                    "minutes_generated": True,
                                    "minutes_text": manual_minutes,
                                    "minutes_generated_at": datetime.now().isoformat()
                                })\
                                .eq("id", meeting_id)\
                                .execute()
                            
                            st.success("✅ Minutes saved successfully!")
                        
                        except Exception as e:
                            st.error(f"Error saving minutes: {str(e)}")
            
            st.divider()
            
            # Show existing minutes if available
            if meeting.get('minutes_text'):
                st.subheader("📄 Current Minutes")
                with st.expander("View Minutes", expanded=False):
                    st.markdown(meeting['minutes_text'])
                
                # Check if minutes_data exists in correct format
                minutes_data = {
                    'minutes_text': meeting.get('minutes_text', ''),
                    'transcript': meeting.get('transcript', '')
                }
                
                if minutes_data.get('minutes_text'):
                    st.download_button(
                        label="📥 Download Minutes (TXT)",
                        data=minutes_data['minutes_text'],
                        file_name=f"{meeting['meeting_title']}_{meeting['meeting_date']}_Minutes.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                
                # Download transcript if exists
                if minutes_data.get('transcript'):
                    st.download_button(
                        label="📝 Download Transcript (TXT)",
                        data=minutes_data['transcript'],
                        file_name=f"{meeting['meeting_title']}_{meeting['meeting_date']}_Transcript.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
            else:
                st.info("No minutes available for download yet.")
            
            # Return button
            st.divider()
            if st.button("↩ Return to Committee", use_container_width=True):
                navigate_to('committee_home', meeting['committee_name'])
    
    except Exception as e:
        st.error(f"Error loading meeting: {str(e)}")
        if st.button("↩ Return"):
            navigate_to('home')

# ========== DOCUMENTS VIEW ==========
elif st.session_state.committee_view == 'documents':
    
    tab1, tab2 = st.tabs(["📄 View Documents", "⬆️ Upload Document"])
    
    with tab1:
        st.subheader("Committee Documents")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("🔍 Search documents", placeholder="Search by name or description...")
        with col2:
            filter_category = st.selectbox("Filter by category", ["All", "Policy", "Procedure", "Meeting Minutes", "Report", "Other"])
        
        try:
            query = supabase.table("committees_documents").select("*").order("upload_date", desc=True)
            
            if filter_category != "All":
                query = query.eq("category", filter_category)
            
            response = query.execute()
            
            if response.data:
                filtered_docs = response.data
                if search_term:
                    filtered_docs = [
                        doc for doc in response.data 
                        if search_term.lower() in doc['document_name'].lower() 
                        or (doc.get('description') and search_term.lower() in doc['description'].lower())
                    ]
                
                if filtered_docs:
                    for doc in filtered_docs:
                        with st.container():
                            col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1.5, 1.5, 1.5])
                            
                            with col1:
                                pin = "📌 " if doc.get('is_current') else ""
                                st.markdown(f"**{pin}{doc['document_name']}**")
                                if doc.get('description'):
                                    st.caption(doc['description'])
                            
                            with col2:
                                if doc.get('category'):
                                    st.caption(f"🏷️ {doc['category']}")
                            
                            with col3:
                                st.caption(f"📅 {doc['upload_date'][:10]}")
                            
                            with col4:
                                st.caption(f"👤 {doc['uploaded_by']}")
                            
                            with col5:
                                try:
                                    signed_url = supabase.storage.from_("committees").create_signed_url(
                                        doc['file_path'], 
                                        3600
                                    )
                                    
                                    if signed_url:
                                        st.link_button(
                                            "👁️",
                                            signed_url['signedURL'],
                                            use_container_width=True
                                        )
                                    
                                    file_data = supabase.storage.from_("committees").download(doc['file_path'])
                                    st.download_button(
                                        label="⬇️",
                                        data=file_data,
                                        file_name=doc['document_name'],
                                        mime=doc.get('mime_type', 'application/octet-stream'),
                                        key=f"download_{doc['id']}",
                                        use_container_width=True
                                    )
                                except Exception as e:
                                    st.error(f"Error: {str(e)[:30]}")
                            
                            st.divider()
                else:
                    st.warning(f"No documents found matching '{search_term}'")
            else:
                st.info("📭 No documents uploaded yet.")
        
        except Exception as e:
            st.error(f"Error loading documents: {str(e)}")
    
    with tab2:
        st.subheader("Upload Committee Document")
        
        with st.form("upload_form"):
            uploaded_file = st.file_uploader(
                "Choose a file",
                type=['pdf', 'docx', 'doc', 'xlsx', 'xls', 'pptx', 'txt']
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                doc_name = st.text_input("Document Name*", placeholder="e.g., Committees Policy 2026")
                category = st.selectbox("Document Category*", ["Policy", "Procedure", "Meeting Minutes", "Report", "Other"])
            
            with col2:
                uploaded_by = st.text_input("Your Name*", placeholder="e.g., Candice")
                is_current_policy = st.checkbox("📌 Mark as current/active policy")
            
            description = st.text_area("Description (optional)", placeholder="Brief description...")
            
            submit = st.form_submit_button("📤 Upload Document", use_container_width=True)
            
            if submit:
                if not uploaded_file or not doc_name or not uploaded_by:
                    st.error("Please complete all required fields.")
                else:
                    try:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        file_path = f"{timestamp}_{uploaded_file.name}"
                        file_bytes = uploaded_file.read()
                        
                        supabase.storage.from_("committees").upload(file_path, file_bytes, {"content-type": uploaded_file.type})
                        
                        supabase.table("committees_documents").insert({
                            "document_name": doc_name,
                            "description": description,
                            "file_path": file_path,
                            "uploaded_by": uploaded_by,
                            "upload_date": datetime.now().isoformat(),
                            "category": category,
                            "mime_type": uploaded_file.type,
                            "file_size": len(file_bytes),
                            "is_current": is_current_policy
                        }).execute()
                        
                        st.success(f"✅ Document '{doc_name}' uploaded successfully!")
                        st.balloons()
                    
                    except Exception as e:
                        st.error(f"Error uploading document: {str(e)}")
    
    st.divider()
    if st.button("↩ Return to Committees Home", use_container_width=True):
        navigate_to('home')

# ========== COMMITTEE MEMBERS VIEW (NEW!) ==========
elif st.session_state.committee_view == 'members':
    
    st.markdown("### 👥 Committee Members & Roles")
    st.markdown("View all staff committee assignments and roles.")
    
    # Back button
    if st.button("↩ Return to Committees Home", use_container_width=True):
        navigate_to('home')
    
    st.divider()
    
    # Try to get committee roles
    try:
        committees = get_all_committee_roles()
        
        if len(committees) == 0:
            st.info("👋 No committee roles found.")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🚀 Initialize Default Committee Roles", use_container_width=True, type="primary"):
                    initialize_default_committee_roles()
                    st.rerun()
        
        else:
            # Edit mode toggle
            edit_mode = st.toggle("✏️ Edit Mode", value=False)
            
            if edit_mode:
                st.info("✏️ **Edit Mode Active** - You can now edit committee members, add new members, or modify committee details.")
                
                # Add new committee option
                with st.expander("➕ Add New Committee"):
                    with st.form("add_new_committee"):
                        new_committee_name = st.text_input("Committee Name")
                        new_committee_desc = st.text_area("Description")
                        
                        if st.form_submit_button("➕ Add Committee", use_container_width=True):
                            if new_committee_name:
                                if add_committee_role(new_committee_name, new_committee_desc):
                                    st.success(f"✅ Added {new_committee_name}")
                                    st.rerun()
                            else:
                                st.error("Please enter a committee name")
            
            st.divider()
            
            # Display committees
            for committee in committees:
                if st.session_state.get(f'editing_{committee["id"]}', False):
                    edit_committee_member_form(committee)
                else:
                    display_committee_member_card(committee, edit_mode=edit_mode)
    
    except Exception as e:
        st.error(f"Error loading committee members: {str(e)}")
        st.info("""
            **Database tables not found.** Please run this SQL in Supabase SQL Editor:
            
            ```sql
            CREATE TABLE IF NOT EXISTS committee_roles (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                display_order INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            
            CREATE TABLE IF NOT EXISTS committee_role_members (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                committee_id UUID REFERENCES committee_roles(id) ON DELETE CASCADE,
                staff_name TEXT NOT NULL,
                role TEXT,
                display_order INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(committee_id, staff_name, role)
            );
            
            CREATE INDEX idx_committee_role_members_committee ON committee_role_members(committee_id);
            CREATE INDEX idx_committee_roles_display_order ON committee_roles(display_order);
            CREATE INDEX idx_committee_role_members_display_order ON committee_role_members(display_order);
            
            ALTER TABLE committee_roles ENABLE ROW LEVEL SECURITY;
            ALTER TABLE committee_role_members ENABLE ROW LEVEL SECURITY;
            
            CREATE POLICY "Allow read for authenticated users" ON committee_roles
                FOR SELECT USING (auth.role() = 'authenticated');
            CREATE POLICY "Allow read for authenticated users" ON committee_role_members
                FOR SELECT USING (auth.role() = 'authenticated');
            CREATE POLICY "Allow all for service role" ON committee_roles
                FOR ALL USING (true);
            CREATE POLICY "Allow all for service role" ON committee_role_members
                FOR ALL USING (true);
            ```
        """)

# ========== FOOTER ==========
st.divider()
st.caption("💡 Tip: Use AI-assisted minutes generation to save time, or enter minutes manually following DfE format.")
