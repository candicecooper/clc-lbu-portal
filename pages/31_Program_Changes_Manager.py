import streamlit as st
from datetime import datetime, date, time
import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import streamlit.components.v1 as components
import io
import json
import uuid
import os
import copy

# Page config
st.set_page_config(page_title="Program Changes Manager", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .main {background-color: #f0f2f6;}
    .stButton>button {
        background-color: #1A7A6E;
        color: white;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #156359;
    }
    .change-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .block-row {
        background-color: #fafcfb;
        border: 1px solid #e0e8e6;
        border-radius: 8px;
        padding: 0.75rem;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ── STAFF LIST PERSISTENCE (Supabase, direct table calls only - no RPC) ──
# Past issues were specifically with custom RPC functions and PostgREST's
# schema cache. Plain table select/insert/delete (same pattern already used
# elsewhere in this portal, e.g. daily_changes) has been reliable. If the
# table isn't reachable for any reason, we fall back to session-only storage
# so the tool keeps working - it just won't remember new staff next visit.

DEFAULT_STAFF = [
    "Candice", "Annette", "Ben Selga", "Ben Sutton", "Caitie",
    "Jacqui", "Brenton", "New Teacher (TBD)", "Naomi", "Vinnie", "Cheryl"
]

STAFF_TABLE = "clc_staff_list"

def _get_supabase():
    """Create a Supabase client from env vars. Returns None if unavailable."""
    try:
        from supabase import create_client
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
        if not url or not key:
            return None
        return create_client(url, key)
    except Exception:
        return None

def load_staff_from_db():
    """Load staff names from Supabase. Returns list or None on failure."""
    sb = _get_supabase()
    if not sb:
        return None
    try:
        res = sb.table(STAFF_TABLE).select("name").order("name").execute()
        names = [r["name"] for r in (res.data or [])]
        return names if names else None
    except Exception:
        return None

def add_staff_to_db(name):
    """Insert a staff name into Supabase. Returns True on success."""
    sb = _get_supabase()
    if not sb:
        return False
    try:
        sb.table(STAFF_TABLE).insert({"name": name}).execute()
        return True
    except Exception:
        return False

def remove_staff_from_db(name):
    """Delete a staff name from Supabase. Returns True on success."""
    sb = _get_supabase()
    if not sb:
        return False
    try:
        sb.table(STAFF_TABLE).delete().eq("name", name).execute()
        return True
    except Exception:
        return False

# ── PROGRAM CHANGES PERSISTENCE (Supabase, direct table calls only) ──
CHANGES_TABLE = "program_changes"

def _parse_time_blocks(raw):
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return []
    return raw or []

def load_changes_from_db(target_date_str):
    """Load program changes for a date from Supabase. Returns list or None on failure."""
    sb = _get_supabase()
    if not sb:
        return None
    try:
        res = sb.table(CHANGES_TABLE).select("*").eq("change_date", target_date_str).order("created_at").execute()
        rows = res.data or []
        for row in rows:
            row['time_blocks'] = _parse_time_blocks(row.get('time_blocks'))
        return rows
    except Exception:
        return None

def insert_change_to_db(change_data):
    """Insert a new program change into Supabase. Returns the new row's id, or None on failure."""
    sb = _get_supabase()
    if not sb:
        return None
    try:
        payload = dict(change_data)
        payload['time_blocks'] = json.dumps(payload.get('time_blocks', []))
        res = sb.table(CHANGES_TABLE).insert(payload).execute()
        if res.data:
            return res.data[0].get('id')
        return None
    except Exception:
        return None

def update_change_in_db(change_id, change_data):
    """Update an existing program change in Supabase. Returns True on success."""
    sb = _get_supabase()
    if not sb:
        return False
    try:
        payload = dict(change_data)
        payload['time_blocks'] = json.dumps(payload.get('time_blocks', []))
        payload['updated_at'] = datetime.now().isoformat()
        payload.pop('id', None)
        payload.pop('created_at', None)
        sb.table(CHANGES_TABLE).update(payload).eq("id", change_id).execute()
        return True
    except Exception:
        return False

def delete_change_from_db(change_id):
    """Delete a program change from Supabase. Returns True on success."""
    sb = _get_supabase()
    if not sb:
        return False
    try:
        sb.table(CHANGES_TABLE).delete().eq("id", change_id).execute()
        return True
    except Exception:
        return False

# Initialize staff list: try DB first, fall back to session/default
if 'staff_list' not in st.session_state:
    db_staff = load_staff_from_db()
    if db_staff:
        st.session_state.staff_list = db_staff
        st.session_state.staff_db_connected = True
    else:
        st.session_state.staff_list = DEFAULT_STAFF.copy()
        st.session_state.staff_db_connected = (db_staff is not None)  # None means DB unreachable

STAFF_LIST = st.session_state.staff_list

# Initialize session state for storing changes
if 'program_changes' not in st.session_state:
    st.session_state.program_changes = {}

# Draft state for add/edit form
def new_draft():
    return {
        'id': None,
        'staff_type': "Regular Staff",
        'staff_member': "",
        'reason': "",
        'covered_by': "",
        'notes': "",
        'blocks': [new_block()],
    }

def new_block():
    return {
        'start_time': time(9, 0),
        'end_time': time(10, 0),
        'program_type': "N/A",
        'lunch_type': "N/A",
        'release_direction': "N/A",
        'release_person': "",
    }

if 'draft' not in st.session_state:
    st.session_state.draft = new_draft()

if 'draft_version' not in st.session_state:
    st.session_state.draft_version = 0

# Helper functions
def format_time(t):
    """Format time object to string"""
    if isinstance(t, time):
        return t.strftime("%I:%M %p").lstrip('0')
    elif isinstance(t, str):
        try:
            return datetime.strptime(t, "%H:%M:%S").strftime("%I:%M %p").lstrip('0')
        except:
            return t
    return str(t)

def parse_time_str(t):
    """Parse HH:MM:SS string back to a time object for widget defaults"""
    if isinstance(t, time):
        return t
    try:
        return datetime.strptime(t, "%H:%M:%S").time()
    except Exception:
        return time(9, 0)

def sort_blocks(blocks):
    """Recalibrate block order by start time, regardless of entry order"""
    return sorted(blocks, key=lambda b: b.get('start_time', ''))

def get_changes_for_date(target_date_str):
    """Get changes for specific date - from database if connected, else session state"""
    db_rows = load_changes_from_db(target_date_str)
    if db_rows is not None:
        st.session_state.pc_db_connected = True
        return db_rows
    st.session_state.pc_db_connected = False
    return st.session_state.program_changes.get(target_date_str, [])

def save_program_change(target_date_str, change_data):
    """Save a NEW program change - to database if connected, else session state"""
    change_data = dict(change_data)
    change_data['change_date'] = target_date_str
    new_id = insert_change_to_db(change_data)
    if new_id:
        st.session_state.pc_db_connected = True
        return
    st.session_state.pc_db_connected = False
    if target_date_str not in st.session_state.program_changes:
        st.session_state.program_changes[target_date_str] = []
    change_data['id'] = str(uuid.uuid4())
    change_data['created_at'] = datetime.now().isoformat()
    st.session_state.program_changes[target_date_str].append(change_data)

def update_program_change(target_date_str, change_id, new_data):
    """Update an EXISTING program change - in database if connected, else session state"""
    new_data = dict(new_data)
    new_data['change_date'] = target_date_str
    if update_change_in_db(change_id, new_data):
        st.session_state.pc_db_connected = True
        return
    st.session_state.pc_db_connected = False
    entries = st.session_state.program_changes.get(target_date_str, [])
    for idx, entry in enumerate(entries):
        if entry.get('id') == change_id:
            new_data['id'] = change_id
            new_data['created_at'] = entry.get('created_at')
            new_data['updated_at'] = datetime.now().isoformat()
            entries[idx] = new_data
            break
    st.session_state.program_changes[target_date_str] = entries

def delete_program_change(target_date_str, change_id):
    """Delete a program change - from database if connected, else session state"""
    if delete_change_from_db(change_id):
        st.session_state.pc_db_connected = True
        return
    st.session_state.pc_db_connected = False
    if target_date_str in st.session_state.program_changes:
        st.session_state.program_changes[target_date_str] = [
            c for c in st.session_state.program_changes[target_date_str]
            if c['id'] != change_id
        ]

def compute_modified_program(program_type, lunch_type):
    if lunch_type != "N/A":
        return f"{program_type} - {lunch_type}"
    return program_type

def compute_release_text(direction, person):
    if direction == "N/A" or not person:
        return ""
    if direction == "Released by":
        return f"Released by {person}"
    else:  # "Releasing"
        return f"Releasing {person}"

def load_all_changes_from_db():
    """Load ALL program changes from Supabase, grouped by date. Returns dict or None on failure."""
    sb = _get_supabase()
    if not sb:
        return None
    try:
        res = sb.table(CHANGES_TABLE).select("*").order("change_date").execute()
        rows = res.data or []
        grouped = {}
        for row in rows:
            row['time_blocks'] = _parse_time_blocks(row.get('time_blocks'))
            d = row.get('change_date')
            grouped.setdefault(d, []).append(row)
        return grouped
    except Exception:
        return None

def export_data():
    """Export all changes and staff list as JSON"""
    db_changes = load_all_changes_from_db()
    changes_to_export = db_changes if db_changes is not None else st.session_state.program_changes
    export_package = {
        'staff_list': st.session_state.staff_list,
        'program_changes': changes_to_export
    }
    return json.dumps(export_package, indent=2)

def import_data(json_str):
    """Import changes and staff list from JSON. Pushes changes into the database when connected."""
    try:
        data = json.loads(json_str)
        changes = data.get('program_changes', data if 'program_changes' not in data else {})
        if 'staff_list' in data:
            st.session_state.staff_list = data['staff_list']

        sb = _get_supabase()
        if sb:
            for date_str, entries in changes.items():
                for entry in entries:
                    entry = dict(entry)
                    entry['change_date'] = date_str
                    entry.pop('id', None)
                    entry.pop('created_at', None)
                    entry.pop('updated_at', None)
                    insert_change_to_db(entry)
        else:
            st.session_state.program_changes = changes
        return True
    except Exception:
        return False

def generate_pdf(changes, target_date):
    """Generate one-page PDF of program changes"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                           topMargin=1*cm, bottomMargin=1*cm,
                           leftMargin=1*cm, rightMargin=1*cm)

    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1A7A6E'),
        alignment=TA_CENTER,
        spaceAfter=12
    )

    title_text = f"Program Changes - {datetime.strptime(target_date, '%Y-%m-%d').strftime('%A, %d %B %Y')}"
    story.append(Paragraph(title_text, title_style))
    story.append(Spacer(1, 0.3*cm))

    if not changes:
        no_changes_style = ParagraphStyle(
            'NoChanges',
            parent=styles['Normal'],
            fontSize=12,
            alignment=TA_CENTER,
            textColor=colors.grey
        )
        story.append(Paragraph("No program changes scheduled for this day", no_changes_style))
    else:
        for idx, change in enumerate(changes):
            staff_name = change.get('staff_name', 'N/A')
            reason = change.get('reason', 'Program Change')
            covered_by = change.get('covered_by', '')

            header_text = f"<b>{staff_name}: {reason}</b>"
            if covered_by:
                header_text += f"<br/><font size=9>Covered by: {covered_by}</font>"

            header_data = [
                [Paragraph(header_text,
                          ParagraphStyle('ChangeHeader', parent=styles['Normal'],
                                       fontSize=11, textColor=colors.HexColor('#1A7A6E')))]
            ]

            header_table = Table(header_data, colWidths=[25*cm])
            header_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E8F4F2')),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(header_table)
            story.append(Spacer(1, 0.2*cm))

            blocks = sort_blocks(change.get('time_blocks', []))
            if blocks:
                for block in blocks:
                    start = format_time(block.get('start_time', ''))
                    end = format_time(block.get('end_time', ''))
                    program = block.get('modified_program', 'N/A')
                    release_text = block.get('released_by', '')

                    block_text = f"{start} → {end}: {program}"
                    if release_text:
                        block_text += f" ({release_text})"

                    details_data = [[block_text]]
                    details_table = Table(details_data, colWidths=[25*cm])
                    details_table.setStyle(TableStyle([
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('PADDING', (0, 0), (-1, -1), 6),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ]))
                    story.append(details_table)

            if idx < len(changes) - 1:
                story.append(Spacer(1, 0.4*cm))

    doc.build(story)
    buffer.seek(0)
    return buffer

def render_mobile_view(changes, target_date):
    """Render mobile-friendly view"""
    date_str = datetime.strptime(target_date, '%Y-%m-%d').strftime('%A, %d %B %Y')

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                margin: 0;
                padding: 20px;
                background: #f0f2f6;
            }}
            .mobile-view {{
                background-color: white;
                padding: 1rem;
                border-radius: 8px;
                max-width: 375px;
                margin: 0 auto;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            .mobile-header {{
                background-color: #1A7A6E;
                color: white;
                padding: 1rem;
                border-radius: 8px 8px 0 0;
                text-align: center;
                font-weight: bold;
                font-size: 1.1rem;
                margin: -1rem -1rem 1rem -1rem;
            }}
            .mobile-change {{
                border-left: 4px solid #C8760A;
                padding-left: 0.75rem;
                margin-bottom: 1.5rem;
                padding-bottom: 1rem;
                border-bottom: 1px solid #eee;
            }}
            .mobile-staff {{
                font-weight: bold;
                color: #1A7A6E;
                font-size: 1.1rem;
                margin-bottom: 0.25rem;
            }}
            .mobile-reason {{
                color: #666;
                font-size: 0.9rem;
                margin: 0.25rem 0 0.5rem 0;
            }}
            .mobile-covered {{
                font-size: 0.85rem;
                color: #1A7A6E;
                font-weight: 600;
                margin: 0.25rem 0;
            }}
            .mobile-blocks {{
                background-color: #f8f9fa;
                padding: 0.5rem;
                border-radius: 4px;
                margin-top: 0.5rem;
                font-size: 0.85rem;
            }}
            .mobile-time {{
                color: #C8760A;
                font-weight: 600;
            }}
            .block-item {{
                margin: 0.25rem 0;
            }}
            .released-by {{
                font-size: 0.8rem;
                color: #888;
                margin-left: 0.5rem;
            }}
        </style>
    </head>
    <body>
        <div class="mobile-view">
            <div class="mobile-header">
                Program Changes<br>
                <span style="font-size: 0.9rem; font-weight: normal;">{date_str}</span>
            </div>
    """

    if not changes:
        html += '<p style="text-align: center; color: #666; padding: 2rem;">No program changes scheduled</p>'
    else:
        for change in changes:
            html += f"""
            <div class="mobile-change">
                <div class="mobile-staff">{change.get('staff_name', 'N/A')}</div>
                <div class="mobile-reason">{change.get('reason', 'Program Change')}</div>
            """

            if change.get('covered_by'):
                html += f'<div class="mobile-covered">Covered by: {change.get("covered_by")}</div>'

            blocks = sort_blocks(change.get('time_blocks', []))
            if blocks:
                html += '<div class="mobile-blocks">'
                for block in blocks:
                    start = format_time(block.get('start_time', ''))
                    end = format_time(block.get('end_time', ''))
                    program = block.get('modified_program', 'N/A')
                    release_text = block.get('released_by', '')

                    html += f'<div class="block-item"><span class="mobile-time">{start} → {end}</span>: {program}'
                    if release_text:
                        html += f'<span class="released-by">({release_text})</span>'
                    html += '</div>'
                html += '</div>'

            html += '</div>'

    html += """
        </div>
    </body>
    </html>
    """
    return html

# ── MAIN INTERFACE ──────────────────────────────────────────────
st.title("📋 Program Changes Manager")

if st.session_state.get('pc_db_connected') is False:
    st.warning("⚠️ Database not reachable right now - changes are only saved for this browser session. Use Export/Import (💾 Data) to keep a backup, and they'll sync once the database is back.")
else:
    st.success("✅ Changes save automatically and appear on the Daily Bulletin for everyone, on any device.")

if st.session_state.get('staff_db_connected') is False:
    st.warning("⚠️ Staff list database not reachable right now - new staff added will only last this session. Use Export/Import (💾 Data) to keep a backup.")

# Date selector
col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
with col1:
    target_date = st.date_input("Select Date", value=date.today(), key="target_date")
with col2:
    st.write("")
    st.write("")
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()
with col3:
    st.write("")
    st.write("")
    with st.popover("👥 Staff", use_container_width=True):
        st.markdown("**Manage Staff List**")

        new_staff_name = st.text_input("Add Staff Member", placeholder="e.g., New Teacher Name", key="new_staff_input")
        if st.button("➕ Add Staff", use_container_width=True, key="add_staff_btn"):
            name = new_staff_name.strip()
            if name:
                if name not in st.session_state.staff_list:
                    st.session_state.staff_list.append(name)
                    saved = add_staff_to_db(name)
                    if saved:
                        st.success(f"✅ Added {name} (saved permanently)")
                    else:
                        st.warning(f"Added {name} for this session only - database not reachable")
                    st.rerun()
                else:
                    st.warning("Already in list")
            else:
                st.warning("Enter a name first")

        st.markdown("---")
        st.markdown("**Current Staff**")

        for staff in list(st.session_state.staff_list):
            scol1, scol2 = st.columns([3, 1])
            with scol1:
                st.write(staff)
            with scol2:
                if st.button("🗑️", key=f"remove_staff_{staff}", help=f"Remove {staff}"):
                    st.session_state.staff_list.remove(staff)
                    remove_staff_from_db(staff)
                    st.rerun()

        st.markdown("---")
        if st.button("↩️ Reset to Default List", use_container_width=True, key="reset_staff_btn"):
            st.session_state.staff_list = DEFAULT_STAFF.copy()
            st.rerun()
with col4:
    st.write("")
    st.write("")
    with st.popover("💾 Data", use_container_width=True):
        st.markdown("**Export Data**")
        st.caption("Includes program changes AND staff list")
        export_json = export_data()
        st.download_button(
            "📥 Download JSON",
            data=export_json,
            file_name=f"program_changes_{date.today().isoformat()}.json",
            mime="application/json",
            use_container_width=True
        )

        st.markdown("**Import Data**")
        uploaded_file = st.file_uploader("Upload JSON", type=['json'], key="import_json")
        if uploaded_file:
            import_json = uploaded_file.read().decode()
            if import_data(import_json):
                st.success("✅ Data imported!")
                st.rerun()

target_date_str = target_date.isoformat()
changes = get_changes_for_date(target_date_str)

st.markdown("---")

# ── ADD / EDIT FORM (not wrapped in st.form, so Add/Remove Block react instantly) ──
editing = st.session_state.draft['id'] is not None
expander_label = "✏️ Editing Timetable Change" if editing else "➕ Add Timetable Change"

with st.expander(expander_label, expanded=(len(changes) == 0 or editing)):
    st.info("""
    **Important:** Only create entries for people WHO ARE ONSITE.

    - **Ben Sutton absent?** → Create an entry for the TRT (e.g. Gary) showing the TRT's timetable
    - **Caitie released for meeting?** → Create an entry for Caitie AND an entry for whoever covers her
    - **Someone picks up extra lunch duty?** → Create an entry for that person

    Each entry = one person's view of what THEY are doing today.
    """)

    if editing:
        ccol1, ccol2 = st.columns([4, 1])
        with ccol1:
            st.markdown(f"**Editing:** {st.session_state.draft.get('staff_member', '')}")
        with ccol2:
            if st.button("✖️ Cancel Edit", use_container_width=True):
                st.session_state.draft = new_draft()
                st.session_state.draft_version += 1
                st.rerun()

    dv = st.session_state.draft_version

    st.subheader("Staff Member (must be onsite)")
    st.caption("Only create entries for people WHO ARE ONSITE. Absent staff don't get entries.")

    col1, col2 = st.columns([1, 3])
    with col1:
        staff_type_idx = 0 if st.session_state.draft['staff_type'] == "Regular Staff" else 1
        staff_type = st.radio(
            "Type",
            options=["Regular Staff", "TRT/Relief"],
            index=staff_type_idx,
            key=f"staff_type_{dv}"
        )
        st.session_state.draft['staff_type'] = staff_type

    with col2:
        if staff_type == "Regular Staff":
            current_staff = st.session_state.draft['staff_member']
            options = STAFF_LIST if current_staff in STAFF_LIST else STAFF_LIST + ([current_staff] if current_staff else [])
            default_idx = options.index(current_staff) if current_staff in options else 0
            staff_member = st.selectbox("Select Staff Member *", options=options, index=default_idx, key=f"staff_select_{dv}")
        else:
            staff_member = st.text_input("TRT/Relief Name *", value=st.session_state.draft['staff_member'],
                                          placeholder="e.g., Gary, Relief Teacher Name", key=f"trt_name_{dv}")
        st.session_state.draft['staff_member'] = staff_member

    st.markdown("---")
    st.subheader(f"Why is {staff_member or 'this person'}'s timetable different today?")

    reason = st.text_input(
        "Reason *",
        value=st.session_state.draft['reason'],
        placeholder="e.g., Covering absent Ben Sutton, Released for PAC Meeting, Extra lunch duty",
        key=f"reason_{dv}"
    )
    st.session_state.draft['reason'] = reason

    col1, col2 = st.columns(2)
    with col1:
        covered_by = st.text_input(
            "If THEY are being covered (optional)",
            value=st.session_state.draft['covered_by'],
            placeholder="e.g., Candice, Gary (TRT)",
            help="Only fill if THIS person is being released/covered by someone else",
            key=f"covered_by_{dv}"
        )
        st.session_state.draft['covered_by'] = covered_by
    with col2:
        notes = st.text_area("Additional Notes", value=st.session_state.draft['notes'],
                              placeholder="Optional notes...", key=f"notes_{dv}")
        st.session_state.draft['notes'] = notes

    st.markdown("---")
    st.subheader(f"{staff_member or 'Their'}'s Timetable for Today")
    st.caption("Blocks are automatically reordered by start time, so you can add them in any order.")

    for i, block in enumerate(st.session_state.draft['blocks']):
        st.markdown('<div class="block-row">', unsafe_allow_html=True)
        bcol1, bcol2, bcol3, bcol4, bcolx = st.columns([2, 2, 2, 2, 0.6])
        with bcol1:
            start_val = block['start_time'] if isinstance(block['start_time'], time) else parse_time_str(block['start_time'])
            start_time_in = st.time_input("Start", value=start_val, key=f"start_{dv}_{i}")
        with bcol2:
            end_val = block['end_time'] if isinstance(block['end_time'], time) else parse_time_str(block['end_time'])
            end_time_in = st.time_input("End", value=end_val, key=f"end_{dv}_{i}")
        with bcol3:
            program_options = ["N/A", "JP", "PY", "SY", "NIT", "PRT", "Lunch Cover", "Meeting", "Other"]
            p_idx = program_options.index(block['program_type']) if block['program_type'] in program_options else 0
            program_type = st.selectbox("Program", options=program_options, index=p_idx, key=f"program_{dv}_{i}")
        with bcol4:
            lunch_options = ["N/A", "Own Lunch", "Lunch Cover"]
            l_idx = lunch_options.index(block['lunch_type']) if block['lunch_type'] in lunch_options else 0
            lunch_type = st.selectbox("Lunch", options=lunch_options, index=l_idx, key=f"lunch_{dv}_{i}")
        with bcolx:
            st.write("")
            st.write("")
            remove_clicked = st.button("🗑️", key=f"remove_block_{dv}_{i}", help="Remove this block") if len(st.session_state.draft['blocks']) > 1 else False

        rcol1, rcol2 = st.columns([1, 2])
        with rcol1:
            direction_options = ["N/A", "Released by", "Releasing"]
            d_idx = direction_options.index(block['release_direction']) if block['release_direction'] in direction_options else 0
            release_direction = st.selectbox(
                "Release",
                options=direction_options,
                index=d_idx,
                key=f"direction_{dv}_{i}",
                help="'Released by X' = X frees this person up. 'Releasing X' = this person frees someone else up."
            )
        with rcol2:
            if release_direction != "N/A":
                person_options = ["(Select)"] + STAFF_LIST + ["Type a name..."]
                current_person = block['release_person']
                if current_person and current_person not in STAFF_LIST:
                    default_person_idx = person_options.index("Type a name...")
                elif current_person in STAFF_LIST:
                    default_person_idx = person_options.index(current_person)
                else:
                    default_person_idx = 0
                person_choice = st.selectbox("Who", options=person_options, index=default_person_idx, key=f"person_choice_{dv}_{i}")
                if person_choice == "Type a name...":
                    release_person = st.text_input("Enter name (e.g. TRT)", value=current_person if current_person not in STAFF_LIST else "",
                                                     key=f"person_manual_{dv}_{i}")
                elif person_choice == "(Select)":
                    release_person = ""
                else:
                    release_person = person_choice
            else:
                release_person = ""
                st.write("")

        # persist this block's live values back to draft
        st.session_state.draft['blocks'][i] = {
            'start_time': start_time_in,
            'end_time': end_time_in,
            'program_type': program_type,
            'lunch_type': lunch_type,
            'release_direction': release_direction,
            'release_person': release_person,
        }

        st.markdown('</div>', unsafe_allow_html=True)

        if remove_clicked:
            st.session_state.draft['blocks'].pop(i)
            st.rerun()

    if st.button("➕ Add Block", key=f"add_block_{dv}"):
        st.session_state.draft['blocks'].append(new_block())
        st.rerun()

    st.markdown("---")
    save_label = "💾 Update Timetable Change" if editing else "💾 Save Timetable Change"
    if st.button(save_label, type="primary", use_container_width=True, key=f"save_{dv}"):
        if not staff_member or not reason:
            st.error("Please fill in Staff Member and Reason")
        elif not st.session_state.draft['blocks']:
            st.error("Please add at least one time block")
        else:
            sorted_blocks = sort_blocks([
                {
                    'start_time': b['start_time'].strftime("%H:%M:%S") if isinstance(b['start_time'], time) else b['start_time'],
                    'end_time': b['end_time'].strftime("%H:%M:%S") if isinstance(b['end_time'], time) else b['end_time'],
                    'program_type': b['program_type'],
                    'lunch_type': b['lunch_type'],
                    'modified_program': compute_modified_program(b['program_type'], b['lunch_type']),
                    'release_direction': b['release_direction'],
                    'release_person': b['release_person'],
                    'released_by': compute_release_text(b['release_direction'], b['release_person']),
                }
                for b in st.session_state.draft['blocks']
            ])

            change_data = {
                'change_date': target_date_str,
                'staff_name': staff_member,
                'reason': reason,
                'covered_by': covered_by if covered_by else None,
                'notes': notes if notes else None,
                'time_blocks': sorted_blocks
            }

            if editing:
                update_program_change(target_date_str, st.session_state.draft['id'], change_data)
                st.success(f"✅ Timetable updated for {staff_member}!")
            else:
                save_program_change(target_date_str, change_data)
                st.success(f"✅ Timetable saved for {staff_member}!")

            st.session_state.draft = new_draft()
            st.session_state.draft_version += 1
            st.rerun()

# ── DISPLAY EXISTING CHANGES ──────────────────────────────────
st.markdown("---")
st.subheader(f"Program Changes for {target_date.strftime('%A, %d %B %Y')}")
st.caption("Each entry = one person's view of their timetable changes")

if not changes:
    st.info("No program changes scheduled for this day")
else:
    for change in changes:
        with st.container():
            st.markdown('<div class="change-card">', unsafe_allow_html=True)

            col1, col2, col3 = st.columns([4, 0.6, 0.6])
            with col1:
                st.markdown(f"### {change.get('staff_name', 'N/A')}: {change.get('reason', 'Program Change')}")
                if change.get('covered_by'):
                    st.markdown(f"**Covered by:** {change.get('covered_by')}")
            with col2:
                if st.button("✏️", key=f"edit_{change['id']}", use_container_width=True, help="Edit this entry"):
                    edit_copy = copy.deepcopy(change)
                    blocks = []
                    for b in sort_blocks(edit_copy.get('time_blocks', [])):
                        blocks.append({
                            'start_time': parse_time_str(b.get('start_time', '')),
                            'end_time': parse_time_str(b.get('end_time', '')),
                            'program_type': b.get('program_type', 'N/A'),
                            'lunch_type': b.get('lunch_type', 'N/A'),
                            'release_direction': b.get('release_direction', 'N/A'),
                            'release_person': b.get('release_person', ''),
                        })
                    st.session_state.draft = {
                        'id': change['id'],
                        'staff_type': "Regular Staff" if change.get('staff_name') in STAFF_LIST else "TRT/Relief",
                        'staff_member': change.get('staff_name', ''),
                        'reason': change.get('reason', ''),
                        'covered_by': change.get('covered_by') or '',
                        'notes': change.get('notes') or '',
                        'blocks': blocks if blocks else [new_block()],
                    }
                    st.session_state.draft_version += 1
                    st.rerun()
            with col3:
                if st.button("🗑️", key=f"del_{change['id']}", use_container_width=True, help="Delete this entry"):
                    delete_program_change(target_date_str, change['id'])
                    st.rerun()

            if change.get('notes'):
                st.markdown(f"*{change.get('notes')}*")

            blocks = sort_blocks(change.get('time_blocks', []))
            if blocks:
                st.markdown("**Timetable:**")
                for block in blocks:
                    time_display = f"{format_time(block.get('start_time', ''))} → {format_time(block.get('end_time', ''))}"
                    program_display = block.get('modified_program', 'N/A')
                    release_text = block.get('released_by', '')

                    if release_text:
                        st.markdown(f"- **{time_display}**: {program_display} *({release_text})*")
                    else:
                        st.markdown(f"- **{time_display}**: {program_display}")

            st.markdown('</div>', unsafe_allow_html=True)

# ── ACTION BUTTONS ──────────────────────────────────────────
st.markdown("---")

if 'show_mobile_view' not in st.session_state:
    st.session_state.show_mobile_view = False

col1, col2 = st.columns(2)

with col1:
    if st.button("📱 Mobile View", use_container_width=True, type="secondary"):
        st.session_state.show_mobile_view = not st.session_state.show_mobile_view

with col2:
    pdf_buffer = generate_pdf(changes, target_date_str)
    st.download_button(
        label="📄 Download PDF",
        data=pdf_buffer,
        file_name=f"program_changes_{target_date_str}.pdf",
        mime="application/pdf",
        use_container_width=True,
        type="primary"
    )

if st.session_state.show_mobile_view:
    st.markdown("---")
    st.markdown("### 📱 Mobile View (Screenshot this for forwarding)")
    mobile_html = render_mobile_view(changes, target_date_str)
    components.html(mobile_html, height=600, scrolling=True)
