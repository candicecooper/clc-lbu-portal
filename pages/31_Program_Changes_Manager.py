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
import base64

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
    .edit-mode-banner {
        background-color: #fff3cd;
        border-left: 4px solid #C8760A;
        padding: 0.75rem 1rem;
        border-radius: 4px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'program_changes' not in st.session_state:
    st.session_state.program_changes = {}
if 'editing_change_id' not in st.session_state:
    st.session_state.editing_change_id = None
if 'editing_change_data' not in st.session_state:
    st.session_state.editing_change_data = None
if 'num_blocks' not in st.session_state:
    st.session_state.num_blocks = 1
if 'show_mobile_view' not in st.session_state:
    st.session_state.show_mobile_view = False

# Staff list — Tom replaces "New Teacher (TBD)"
STAFF_LIST = [
    "Candice", "Annette", "Ben Selga", "Ben Sutton", "Caitie",
    "Jacqui", "Brenton", "Tom", "Naomi", "Vinnie", "Cheryl"
]

# Program/Role options — Lunch options now live here; no separate Lunch column
PROGRAM_OPTIONS = [
    "JP", "PY", "SY", "NIT", "PRT",
    "Meeting", "Own Lunch", "Lunch Release", "Other"
]

# ─────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────

def parse_time(time_str):
    """Parse stored time string back to a time object."""
    try:
        if isinstance(time_str, time):
            return time_str
        parts = str(time_str).split(':')
        return time(int(parts[0]), int(parts[1]))
    except Exception:
        return time(9, 0)


def format_time(t):
    """Format time object to display string."""
    if isinstance(t, time):
        return t.strftime("%I:%M %p").lstrip('0')
    elif isinstance(t, str):
        try:
            return datetime.strptime(t, "%H:%M:%S").strftime("%I:%M %p").lstrip('0')
        except Exception:
            return t
    return str(t)


def get_changes_for_date(target_date_str):
    return st.session_state.program_changes.get(target_date_str, [])


def save_program_change(target_date_str, change_data):
    if target_date_str not in st.session_state.program_changes:
        st.session_state.program_changes[target_date_str] = []
    change_data['id'] = str(uuid.uuid4())
    change_data['created_at'] = datetime.now().isoformat()
    st.session_state.program_changes[target_date_str].append(change_data)


def update_program_change(target_date_str, change_id, new_data):
    """Overwrite an existing entry, preserving id and created_at."""
    if target_date_str in st.session_state.program_changes:
        for i, c in enumerate(st.session_state.program_changes[target_date_str]):
            if c['id'] == change_id:
                new_data['id'] = change_id
                new_data['created_at'] = c.get('created_at', datetime.now().isoformat())
                new_data['updated_at'] = datetime.now().isoformat()
                st.session_state.program_changes[target_date_str][i] = new_data
                break


def delete_program_change(target_date_str, change_id):
    if target_date_str in st.session_state.program_changes:
        st.session_state.program_changes[target_date_str] = [
            c for c in st.session_state.program_changes[target_date_str]
            if c['id'] != change_id
        ]


def export_data():
    return json.dumps(st.session_state.program_changes, indent=2)


def import_data(json_str):
    try:
        st.session_state.program_changes = json.loads(json_str)
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────
# PDF generation
# ─────────────────────────────────────────────

def generate_pdf(changes, target_date):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                            topMargin=1*cm, bottomMargin=1*cm,
                            leftMargin=1*cm, rightMargin=1*cm)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Heading1'],
        fontSize=16, textColor=colors.HexColor('#1A7A6E'),
        alignment=TA_CENTER, spaceAfter=12
    )
    title_text = f"Program Changes - {datetime.strptime(target_date, '%Y-%m-%d').strftime('%A, %d %B %Y')}"
    story.append(Paragraph(title_text, title_style))
    story.append(Spacer(1, 0.3*cm))

    if not changes:
        no_changes_style = ParagraphStyle(
            'NoChanges', parent=styles['Normal'],
            fontSize=12, alignment=TA_CENTER, textColor=colors.grey
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

            header_table = Table(
                [[Paragraph(header_text, ParagraphStyle(
                    'ChangeHeader', parent=styles['Normal'],
                    fontSize=11, textColor=colors.HexColor('#1A7A6E')))
                ]],
                colWidths=[25*cm]
            )
            header_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E8F4F2')),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(header_table)
            story.append(Spacer(1, 0.2*cm))

            blocks = change.get('time_blocks', [])
            for block in blocks:
                start = format_time(block.get('start_time', ''))
                end = format_time(block.get('end_time', ''))
                program = block.get('modified_program', 'N/A')
                released_by = block.get('released_by', '')

                block_text = f"{start} → {end}: {program}"
                if released_by:
                    block_text += f" (Release: {released_by})"

                details_table = Table([[block_text]], colWidths=[25*cm])
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


# ─────────────────────────────────────────────
# Mobile view HTML
# ─────────────────────────────────────────────

def render_mobile_view(changes, target_date):
    """Render a self-contained mobile HTML page — no scrolling, with inline download."""
    date_str = datetime.strptime(target_date, '%Y-%m-%d').strftime('%A, %d %B %Y')

    blocks_html = ""
    if not changes:
        blocks_html = '<p style="text-align:center;color:#666;padding:2rem;">No program changes scheduled</p>'
    else:
        for change in changes:
            covered_html = ""
            if change.get('covered_by'):
                covered_html = f'<div class="mobile-covered">Covered by: {change["covered_by"]}</div>'

            time_rows = ""
            for block in change.get('time_blocks', []):
                start = format_time(block.get('start_time', ''))
                end = format_time(block.get('end_time', ''))
                prog = block.get('modified_program', 'N/A')
                rb = block.get('released_by', '')
                rb_html = f' <span class="released-by">(Release: {rb})</span>' if rb else ''
                time_rows += f'<div class="block-item"><span class="mobile-time">{start} → {end}</span>: {prog}{rb_html}</div>'

            blocks_section = f'<div class="mobile-blocks">{time_rows}</div>' if time_rows else ''
            notes_html = f'<div class="mobile-notes">{change["notes"]}</div>' if change.get('notes') else ''

            blocks_html += f"""
            <div class="mobile-change">
                <div class="mobile-staff">{change.get('staff_name', 'N/A')}</div>
                <div class="mobile-reason">{change.get('reason', 'Program Change')}</div>
                {covered_html}
                {blocks_section}
                {notes_html}
            </div>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f0f2f6;
            padding: 12px;
        }}
        .mobile-view {{
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            width: 100%;
            max-width: 420px;
            margin: 0 auto;
        }}
        .mobile-header {{
            background: #1A7A6E;
            color: white;
            padding: 14px 16px;
            text-align: center;
            font-weight: bold;
            font-size: 1.1rem;
            line-height: 1.4;
        }}
        .mobile-header span {{
            font-size: 0.88rem;
            font-weight: normal;
            display: block;
            opacity: 0.9;
        }}
        .mobile-body {{
            padding: 12px 14px;
        }}
        .mobile-change {{
            border-left: 4px solid #C8760A;
            padding: 8px 10px;
            margin-bottom: 14px;
            padding-bottom: 12px;
            border-bottom: 1px solid #eee;
        }}
        .mobile-change:last-child {{ border-bottom: none; margin-bottom: 0; }}
        .mobile-staff {{
            font-weight: bold;
            color: #1A7A6E;
            font-size: 1rem;
            margin-bottom: 2px;
        }}
        .mobile-reason {{
            color: #555;
            font-size: 0.85rem;
            margin-bottom: 6px;
        }}
        .mobile-covered {{
            font-size: 0.82rem;
            color: #1A7A6E;
            font-weight: 600;
            margin-bottom: 6px;
        }}
        .mobile-blocks {{
            background: #f8f9fa;
            padding: 8px 10px;
            border-radius: 5px;
            font-size: 0.82rem;
        }}
        .block-item {{ margin: 4px 0; line-height: 1.4; }}
        .mobile-time {{ color: #C8760A; font-weight: 600; }}
        .released-by {{ color: #888; font-size: 0.78rem; }}
        .mobile-notes {{
            font-size: 0.8rem;
            color: #666;
            font-style: italic;
            margin-top: 6px;
        }}
        .mobile-footer {{
            padding: 10px 14px;
            border-top: 1px solid #eee;
            text-align: center;
        }}
        .download-btn {{
            display: inline-block;
            background: #1A7A6E;
            color: white;
            padding: 8px 20px;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 600;
            text-decoration: none;
            margin: 4px;
        }}
        .print-btn {{
            display: inline-block;
            background: #C8760A;
            color: white;
            padding: 8px 20px;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            border: none;
            margin: 4px;
        }}
        @media print {{
            .mobile-footer {{ display: none; }}
            body {{ padding: 0; background: white; }}
            .mobile-view {{ box-shadow: none; border-radius: 0; max-width: 100%; }}
        }}
    </style>
</head>
<body>
    <div class="mobile-view">
        <div class="mobile-header">
            Program Changes
            <span>{date_str}</span>
        </div>
        <div class="mobile-body">
            {blocks_html}
        </div>
        <div class="mobile-footer">
            <button class="print-btn" onclick="window.print()">🖨️ Print / Save PDF</button>
        </div>
    </div>
</body>
</html>"""
    return html


# ─────────────────────────────────────────────
# Main interface
# ─────────────────────────────────────────────

st.title("📋 Program Changes Manager")
st.info("⚠️ **Session-Based Storage**: Changes are stored in your browser session. Use Export/Import to save permanently.")

# Date selector + data controls
col1, col2, col3 = st.columns([2, 1, 1])
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
    with st.popover("💾 Data"):
        st.markdown("**Export Data**")
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
            import_json_str = uploaded_file.read().decode()
            if import_data(import_json_str):
                st.success("✅ Data imported!")
                st.rerun()

target_date_str = target_date.isoformat()
changes = get_changes_for_date(target_date_str)

st.markdown("---")

# ─────────────────────────────────────────────
# Add / Edit form
# ─────────────────────────────────────────────

is_editing = st.session_state.editing_change_id is not None
edit_data = st.session_state.editing_change_data or {}

form_title = "✏️ Edit Timetable Entry" if is_editing else "➕ Add Timetable Change"
with st.expander(form_title, expanded=is_editing or len(changes) == 0):

    if is_editing:
        st.markdown(
            f'<div class="edit-mode-banner">✏️ <b>Edit mode</b> — editing entry for <b>{edit_data.get("staff_name", "")}</b>. '
            f'Make your changes below and click <b>Update Timetable</b> to save.</div>',
            unsafe_allow_html=True
        )
        if st.button("❌ Cancel Edit", type="secondary"):
            st.session_state.editing_change_id = None
            st.session_state.editing_change_data = None
            st.session_state.num_blocks = 1
            st.rerun()

    if not is_editing:
        st.info("""
**Important:** Only create entries for people WHO ARE ONSITE.

- **Ben Sutton absent?** → Create entry for the TRT (e.g. Gary) showing Gary's timetable
- **Caitie released for a meeting?** → Create an entry for Caitie AND one for whoever covers her
- **Someone picks up extra lunch duty?** → Create entry for that person

Each entry = one person's view of what THEY are doing today.
""")

    # ── Staff type selector (outside form so it refreshes immediately) ──
    st.subheader("Staff Member (must be onsite)")
    st.caption("Only create entries for people WHO ARE ONSITE. Absent staff don't get entries.")

    col1, col2 = st.columns([1, 3])
    with col1:
        staff_type = st.radio(
            "Type",
            options=["Regular Staff", "TRT/Relief"],
            key="staff_type_selector"
        )
    with col2:
        if staff_type == "Regular Staff":
            staff_member = st.selectbox(
                "Select Staff Member *",
                options=STAFF_LIST,
                key="staff_select_main"
            )
        else:
            staff_member = st.text_input(
                "TRT/Relief Name *",
                placeholder="e.g., Gary, Sarah Relief",
                key="trt_name_main"
            )

    if not staff_member:
        st.warning("⬆️ Please select or enter a staff member name above")
        st.stop()

    # ── Main form ──
    with st.form("new_change_form"):
        st.info(f"📝 {'Editing' if is_editing else 'Creating'} timetable for: **{staff_member}**")
        st.markdown("---")
        st.subheader(f"Why is {staff_member}'s timetable different today?")

        reason = st.text_input(
            "Reason *",
            key="form_reason",
            placeholder="e.g., Covering absent Ben Sutton, Released for PAC Meeting, Lunch cover"
        )

        # covered_by only shown for Regular Staff — TRT/Relief don't need it
        if staff_type == "Regular Staff":
            col1, col2 = st.columns(2)
            with col1:
                covered_by = st.text_input(
                    "If THEY are being covered (optional)",
                    key="form_covered_by",
                    placeholder="e.g., Candice, Tom",
                    help="Only fill if THIS person is being released/covered by someone else"
                )
            with col2:
                notes = st.text_area(
                    "Additional Notes",
                    key="form_notes",
                    placeholder="Optional notes..."
                )
        else:
            covered_by = None
            notes = st.text_area(
                "Additional Notes",
                key="form_notes",
                placeholder="Optional notes..."
            )

        st.markdown("---")
        st.subheader(f"{staff_member}'s Timetable for Today")
        st.caption(
            "Enter each block. **Program/Role** now includes Own Lunch and Lunch Release — "
            "no separate lunch column needed."
        )

        # ── Time blocks ──
        edit_blocks = edit_data.get('time_blocks', []) if is_editing else []

        time_blocks = []
        for i in range(st.session_state.num_blocks):
            eb = edit_blocks[i] if (is_editing and i < len(edit_blocks)) else {}

            st.markdown(f"**Block {i + 1}**")
            bcol1, bcol2, bcol3, bcol4 = st.columns([2, 2, 3, 3])

            with bcol1:
                start_time = st.time_input(
                    "Start",
                    value=time(9, 0),
                    key=f"start_{i}"
                )
            with bcol2:
                end_time = st.time_input(
                    "End",
                    value=time(10, 0),
                    key=f"end_{i}"
                )
            with bcol3:
                program_type = st.selectbox(
                    "Program/Role",
                    options=PROGRAM_OPTIONS,
                    key=f"program_type_{i}"
                )
            with bcol4:
                # Release: dropdown of known staff + manual text box for TRT names
                release_options = ["N/A"] + [s for s in STAFF_LIST if s != staff_member]
                released_by_sel = st.selectbox(
                    "Release",
                    options=release_options,
                    key=f"released_by_{i}",
                    help="Who releases this person for lunch/NIT/break?"
                )
                released_by_manual = st.text_input(
                    "or type name",
                    placeholder="e.g., TRT name...",
                    key=f"released_by_manual_{i}",
                    label_visibility="collapsed"
                )

            # Manual entry takes priority; dropdown used if not N/A; else blank
            if released_by_manual.strip():
                released_by = released_by_manual.strip()
            elif released_by_sel != "N/A":
                released_by = released_by_sel
            else:
                released_by = ""

            time_blocks.append({
                'start_time': start_time.strftime("%H:%M:%S"),
                'end_time': end_time.strftime("%H:%M:%S"),
                'modified_program': program_type,
                'program_type': program_type,
                'released_by': released_by
            })

        # Add block / submit
        col_add, col_spacer = st.columns([1, 4])
        with col_add:
            if st.form_submit_button("➕ Add Block"):
                st.session_state.num_blocks += 1
                st.rerun()

        st.markdown("---")
        btn_label = "💾 Update Timetable" if is_editing else "💾 Save Timetable Change"
        submitted = st.form_submit_button(btn_label, type="primary", use_container_width=True)

        if submitted:
            if not staff_member or not reason:
                st.error("Please fill in Staff Member and Reason")
                st.stop()

            valid_blocks = [b for b in time_blocks if b.get('program_type')]
            if not valid_blocks:
                st.error("Please add at least one time block")
                st.stop()

            change_data = {
                'change_date': target_date_str,
                'staff_name': staff_member,
                'reason': reason,
                'covered_by': covered_by if covered_by else None,
                'notes': st.session_state.get('form_notes') or None,
                'time_blocks': valid_blocks
            }

            if is_editing:
                update_program_change(
                    target_date_str,
                    st.session_state.editing_change_id,
                    change_data
                )
                st.success(f"✅ Timetable updated for {staff_member}!")
                st.session_state.editing_change_id = None
                st.session_state.editing_change_data = None
            else:
                save_program_change(target_date_str, change_data)
                st.success(f"✅ Timetable saved for {staff_member}!")

            st.session_state.num_blocks = 1
            # Clear form fields
            for key in ['form_reason', 'form_covered_by', 'form_notes']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()


# ─────────────────────────────────────────────
# Display existing changes
# ─────────────────────────────────────────────

st.markdown("---")
st.subheader(f"Program Changes for {target_date.strftime('%A, %d %B %Y')}")
st.caption("Each entry = one person's view of their timetable changes")

if not changes:
    st.info("No program changes scheduled for this day")
else:
    for idx, change in enumerate(changes):
        with st.container():
            st.markdown('<div class="change-card">', unsafe_allow_html=True)

            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                updated_tag = " *(edited)*" if change.get('updated_at') else ""
                st.markdown(
                    f"### {change.get('staff_name', 'N/A')}: {change.get('reason', 'Program Change')}{updated_tag}"
                )
                if change.get('covered_by'):
                    st.markdown(f"**Covered by:** {change.get('covered_by')}")
            with col2:
                if st.button("✏️ Edit", key=f"edit_{change['id']}", use_container_width=True):
                    # Store editing context
                    st.session_state.editing_change_id = change['id']
                    st.session_state.editing_change_data = change

                    # Pre-populate staff selector
                    edit_staff = change.get('staff_name', '')
                    if edit_staff in STAFF_LIST:
                        st.session_state['staff_type_selector'] = "Regular Staff"
                        st.session_state['staff_select_main'] = edit_staff
                    else:
                        st.session_state['staff_type_selector'] = "TRT/Relief"
                        st.session_state['trt_name_main'] = edit_staff

                    # Pre-populate reason / notes / covered_by
                    st.session_state['form_reason'] = change.get('reason', '')
                    st.session_state['form_covered_by'] = change.get('covered_by') or ''
                    st.session_state['form_notes'] = change.get('notes') or ''

                    # Pre-populate time blocks
                    edit_blocks = change.get('time_blocks', [])
                    st.session_state.num_blocks = max(1, len(edit_blocks))
                    for i, block in enumerate(edit_blocks):
                        st.session_state[f'start_{i}'] = parse_time(block.get('start_time', '09:00:00'))
                        st.session_state[f'end_{i}'] = parse_time(block.get('end_time', '10:00:00'))
                        prog = block.get('program_type', 'JP')
                        st.session_state[f'program_type_{i}'] = prog if prog in PROGRAM_OPTIONS else PROGRAM_OPTIONS[0]
                        stored_rb = block.get('released_by', '')
                        if stored_rb in STAFF_LIST:
                            st.session_state[f'released_by_{i}'] = stored_rb
                            st.session_state[f'released_by_manual_{i}'] = ''
                        else:
                            st.session_state[f'released_by_{i}'] = 'N/A'
                            st.session_state[f'released_by_manual_{i}'] = stored_rb

                    st.rerun()

            with col3:
                if st.button("🗑️", key=f"del_{change['id']}", use_container_width=True):
                    delete_program_change(target_date_str, change['id'])
                    st.rerun()

            if change.get('notes'):
                st.markdown(f"*{change.get('notes')}*")

            blocks = change.get('time_blocks', [])
            if blocks:
                st.markdown("**Timetable:**")
                for block in blocks:
                    time_display = (
                        f"{format_time(block.get('start_time', ''))} → "
                        f"{format_time(block.get('end_time', ''))}"
                    )
                    program_display = block.get('modified_program', 'N/A')
                    released_by = block.get('released_by', '')

                    if released_by:
                        st.markdown(
                            f"- **{time_display}**: {program_display} *(Release: {released_by})*"
                        )
                    else:
                        st.markdown(f"- **{time_display}**: {program_display}")

            st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Action buttons — PDF + Mobile view
# ─────────────────────────────────────────────

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    if st.button("📱 Mobile View / Screenshot", use_container_width=True, type="secondary"):
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

# ── Mobile view panel ──
if st.session_state.show_mobile_view:
    st.markdown("---")
    st.markdown("### 📱 Mobile View")
    st.caption(
        "The panel below shows the full timetable in phone-friendly format. "
        "Scroll down past it to download the HTML file to your phone, or use the Print button embedded inside the view."
    )

    mobile_html = render_mobile_view(changes, target_date_str)

    # Calculate a generous height so no iframe scrolling is needed
    estimated_height = 260  # header + footer + padding
    for change in changes:
        estimated_height += 120  # base per entry
        estimated_height += len(change.get('time_blocks', [])) * 45  # per block row
        if change.get('notes'):
            estimated_height += 30
    estimated_height = max(500, estimated_height)

    components.html(mobile_html, height=estimated_height, scrolling=False)

    st.markdown(" ")  # spacing
    # Download the HTML so it can be opened on a phone browser or texted
    mobile_html_bytes = mobile_html.encode('utf-8')
    st.download_button(
        label="📲 Download Mobile HTML (open on phone or text to staff)",
        data=mobile_html_bytes,
        file_name=f"program_changes_{target_date_str}.html",
        mime="text/html",
        use_container_width=True,
        type="secondary"
    )
    st.caption(
        "💡 Tip: download the HTML file and open it in any mobile browser — "
        "it will display cleanly and can be printed or screenshotted without scrolling."
    )
