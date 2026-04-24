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
    .mobile-view {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        max-width: 375px;
        margin: 0 auto;
    }
    .mobile-header {
        background-color: #1A7A6E;
        color: white;
        padding: 1rem;
        border-radius: 8px 8px 0 0;
        text-align: center;
        font-weight: bold;
        font-size: 1.1rem;
        margin: -1rem -1rem 1rem -1rem;
    }
    .mobile-change {
        border-left: 4px solid #C8760A;
        padding-left: 0.75rem;
        margin-bottom: 1rem;
    }
    .mobile-staff {
        font-weight: bold;
        color: #1A7A6E;
        font-size: 1rem;
    }
    .mobile-reason {
        color: #666;
        font-size: 0.9rem;
        margin: 0.25rem 0;
    }
    .mobile-blocks {
        background-color: #f8f9fa;
        padding: 0.5rem;
        border-radius: 4px;
        margin-top: 0.5rem;
        font-size: 0.85rem;
    }
    .mobile-time {
        color: #C8760A;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for storing changes
if 'program_changes' not in st.session_state:
    st.session_state.program_changes = {}

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

def get_changes_for_date(target_date_str):
    """Get changes for specific date from session state"""
    return st.session_state.program_changes.get(target_date_str, [])

def save_program_change(target_date_str, change_data):
    """Save a program change to session state"""
    if target_date_str not in st.session_state.program_changes:
        st.session_state.program_changes[target_date_str] = []
    
    change_data['id'] = str(uuid.uuid4())
    change_data['created_at'] = datetime.now().isoformat()
    st.session_state.program_changes[target_date_str].append(change_data)

def delete_program_change(target_date_str, change_id):
    """Delete a program change from session state"""
    if target_date_str in st.session_state.program_changes:
        st.session_state.program_changes[target_date_str] = [
            c for c in st.session_state.program_changes[target_date_str] 
            if c['id'] != change_id
        ]

def export_data():
    """Export all changes as JSON"""
    return json.dumps(st.session_state.program_changes, indent=2)

def import_data(json_str):
    """Import changes from JSON"""
    try:
        st.session_state.program_changes = json.loads(json_str)
        return True
    except:
        return False

def generate_pdf(changes, target_date):
    """Generate one-page PDF of program changes"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                           topMargin=1*cm, bottomMargin=1*cm,
                           leftMargin=1*cm, rightMargin=1*cm)
    
    story = []
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1A7A6E'),
        alignment=TA_CENTER,
        spaceAfter=12
    )
    
    # Add title
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
        # Build table data
        for idx, change in enumerate(changes):
            # Change header
            header_data = [
                [Paragraph(f"<b>Change {idx + 1}: {change.get('reason', 'Program Change')}</b>", 
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
            
            # Details table
            details_data = [
                ['Staff Member:', change.get('staff_name', 'N/A')],
                ['TRT/Acting:', change.get('trt_name', 'N/A') if change.get('trt_name') else 'N/A'],
            ]
            
            # Add time blocks
            blocks = change.get('time_blocks', [])
            if blocks:
                blocks_text = " | ".join([f"{format_time(b.get('start_time', ''))} → {format_time(b.get('end_time', ''))}: {b.get('modified_program', 'N/A')}" 
                                         for b in blocks])
                details_data.append(['Time Changes:', blocks_text])
            
            details_table = Table(details_data, colWidths=[4*cm, 21*cm])
            details_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F5F5F5')),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1A7A6E')),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(details_table)
            
            if idx < len(changes) - 1:
                story.append(Spacer(1, 0.4*cm))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def render_mobile_view(changes, target_date):
    """Render mobile-friendly view with inline CSS"""
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
            }}
            .mobile-staff {{
                font-weight: bold;
                color: #1A7A6E;
                font-size: 1rem;
                margin-bottom: 0.25rem;
            }}
            .mobile-reason {{
                color: #666;
                font-size: 0.9rem;
                margin: 0.25rem 0;
            }}
            .mobile-trt {{
                font-size: 0.85rem;
                color: #666;
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
        for idx, change in enumerate(changes):
            html += f"""
            <div class="mobile-change">
                <div class="mobile-staff">{change.get('staff_name', 'N/A')}</div>
                <div class="mobile-reason">{change.get('reason', 'Program Change')}</div>
            """
            
            if change.get('trt_name'):
                html += f'<div class="mobile-trt">TRT: {change.get("trt_name")}</div>'
            
            blocks = change.get('time_blocks', [])
            if blocks:
                html += '<div class="mobile-blocks">'
                for block in blocks:
                    start = format_time(block.get('start_time', ''))
                    end = format_time(block.get('end_time', ''))
                    program = block.get('modified_program', 'N/A')
                    html += f'<div class="block-item"><span class="mobile-time">{start} → {end}</span>: {program}</div>'
                html += '</div>'
            
            html += '</div>'
    
    html += """
        </div>
    </body>
    </html>
    """
    return html

# Main interface
st.title("📋 Program Changes Manager")
st.info("⚠️ **Session-Based Storage**: Changes are stored in your browser session and will be lost when you close the tab. Use Export/Import to save permanently.")

# Date selector
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
            import_json = uploaded_file.read().decode()
            if import_data(import_json):
                st.success("✅ Data imported!")
                st.rerun()

target_date_str = target_date.isoformat()

# Get existing changes
changes = get_changes_for_date(target_date_str)

# Main interface continues
st.markdown("---")

# Add new change section
with st.expander("➕ Add New Program Change", expanded=len(changes) == 0):
    
    # Staff list
    staff_list = [
        "Candice", "Annette", "Ben Selga", "Ben Sutton", "Caitie", 
        "Jacqui", "Brenton", "New Teacher (TBD)", "Naomi", "Vinnie", "Cheryl"
    ]
    
    with st.form("new_change_form"):
        st.subheader("Change Type")
        
        change_type = st.radio(
            "What type of change is this?",
            options=[
                "Teacher Absence (TRT Cover)", 
                "Staff Member Released (by another staff member)",
                "Site Need / Program Change"
            ],
            horizontal=False
        )
        
        st.markdown("---")
        st.subheader("Details")
        
        # SCENARIO 1: Teacher Absence (TRT Cover)
        if change_type == "Teacher Absence (TRT Cover)":
            col1, col2 = st.columns(2)
            with col1:
                absent_teacher = st.selectbox("Absent Staff Member *", options=staff_list)
                absence_reason = st.selectbox(
                    "Reason for Absence *",
                    options=["Sick Leave", "Personal Leave", "Professional Learning", "Meeting", "Other"]
                )
            with col2:
                no_trt = st.checkbox("No TRT Available")
                if not no_trt:
                    trt_name = st.text_input("TRT Name *", placeholder="e.g., Gary, Relief Teacher Name")
                else:
                    trt_name = "No TRT"
                notes = st.text_area("Additional Notes", placeholder="Optional notes...")
            
            st.info(f"📋 **{absent_teacher} absent - {absence_reason}** | TRT: {trt_name}")
            staff_for_display = absent_teacher
            reason_for_display = f"{absence_reason} (TRT: {trt_name})"
            releasing_staff = None
            released_for = None
            
        # SCENARIO 2: Staff Member Released
        elif change_type == "Staff Member Released (by another staff member)":
            col1, col2 = st.columns(2)
            with col1:
                released_staff = st.selectbox("Staff Member Being Released *", options=staff_list)
                released_for = st.text_input("Released For *", placeholder="e.g., PAC Meeting, Student Support Meeting")
            with col2:
                # Remove the released staff from the list of who can release them
                releasing_options = [s for s in staff_list if s != released_staff]
                releasing_staff = st.selectbox("Released By (who covers their timetable) *", options=releasing_options)
                notes = st.text_area("Additional Notes", placeholder="Optional notes...")
            
            st.info(f"📋 **{released_staff} released for {released_for}** | Covered by: {releasing_staff}")
            st.warning(f"⚠️ This will create TWO changes: one for {released_staff} and one for {releasing_staff} (if they don't already have a change)")
            staff_for_display = released_staff
            reason_for_display = f"Released for {released_for} (Covered by {releasing_staff})"
            trt_name = None
            
        # SCENARIO 3: Site Need / Program Change
        else:  # Site Need / Program Change
            col1, col2 = st.columns(2)
            with col1:
                affected_staff = st.selectbox("Staff Member Affected *", options=staff_list)
                change_reason = st.text_input("Reason for Change *", placeholder="e.g., Program restructure, Special event")
            with col2:
                impact_note = st.text_input("Impact Note", placeholder="e.g., Temporary change, Full day")
                notes = st.text_area("Additional Notes", placeholder="Optional notes...")
            
            st.info(f"📋 **{affected_staff}'s program changing:** {change_reason}")
            staff_for_display = affected_staff
            reason_for_display = change_reason
            trt_name = None
            releasing_staff = None
            released_for = None
        
        st.markdown("---")
        st.subheader("Timetable Impact")
        st.caption("Which blocks of the timetable are affected?")
        
        # Dynamic time blocks
        if 'num_blocks' not in st.session_state:
            st.session_state.num_blocks = 1
        
        time_blocks = []
        for i in range(st.session_state.num_blocks):
            st.markdown(f"**Block {i + 1}**")
            bcol1, bcol2, bcol3, bcol4 = st.columns([2, 2, 2, 2])
            with bcol1:
                start_time = st.time_input(f"Start Time", value=time(9, 0), key=f"start_{i}")
            with bcol2:
                end_time = st.time_input(f"End Time", value=time(10, 0), key=f"end_{i}")
            with bcol3:
                program_type = st.selectbox(
                    f"Program",
                    options=["JP", "PY", "SY", "NIT", "PRT", "Meeting", "Other"],
                    key=f"program_type_{i}"
                )
            with bcol4:
                lunch_type = st.selectbox(
                    f"Lunch",
                    options=["N/A", "Cover", "Own Lunch"],
                    key=f"lunch_type_{i}"
                )
            
            # Combine program info
            program_text = program_type
            if lunch_type != "N/A":
                program_text = f"{program_type} - {lunch_type}"
            
            time_blocks.append({
                'start_time': start_time.strftime("%H:%M:%S"),
                'end_time': end_time.strftime("%H:%M:%S"),
                'modified_program': program_text,
                'program_type': program_type,
                'lunch_type': lunch_type
            })
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.form_submit_button("➕ Add Block"):
                st.session_state.num_blocks += 1
                st.rerun()
        
        st.markdown("---")
        submitted = st.form_submit_button("💾 Save Program Change", type="primary", use_container_width=True)
        
        if submitted:
            # Validation
            if change_type == "Teacher Absence (TRT Cover)":
                if not absent_teacher or (not no_trt and not trt_name):
                    st.error("Please fill in all required fields")
                    st.stop()
            elif change_type == "Staff Member Released (by another staff member)":
                if not released_staff or not released_for or not releasing_staff:
                    st.error("Please fill in all required fields")
                    st.stop()
            else:
                if not affected_staff or not change_reason:
                    st.error("Please fill in all required fields")
                    st.stop()
            
            # Filter out empty blocks
            valid_blocks = [b for b in time_blocks if b.get('program_type')]
            
            if not valid_blocks:
                st.error("Please add at least one time block")
                st.stop()
            
            # Save the primary change
            change_data = {
                'change_date': target_date_str,
                'change_type': change_type,
                'staff_name': staff_for_display,
                'reason': reason_for_display,
                'trt_name': trt_name if change_type == "Teacher Absence (TRT Cover)" else None,
                'notes': notes if notes else None,
                'time_blocks': valid_blocks
            }
            
            save_program_change(target_date_str, change_data)
            
            # SCENARIO 2: Create second change for releasing staff member
            if change_type == "Staff Member Released (by another staff member)" and releasing_staff:
                # Check if releasing staff already has a change for these times
                existing_changes = get_changes_for_date(target_date_str)
                releasing_staff_has_change = any(
                    c.get('staff_name') == releasing_staff 
                    for c in existing_changes
                )
                
                if not releasing_staff_has_change:
                    # Create automatic second change
                    releasing_change_data = {
                        'change_date': target_date_str,
                        'change_type': 'Auto-generated (Covering Released Staff)',
                        'staff_name': releasing_staff,
                        'reason': f"Covering {released_staff}'s {', '.join([b['program_type'] for b in valid_blocks])} while they attend {released_for}",
                        'trt_name': None,
                        'notes': f"Auto-created: Releasing {released_staff}",
                        'time_blocks': valid_blocks
                    }
                    save_program_change(target_date_str, releasing_change_data)
                    st.success(f"✅ Created changes for both {released_staff} (released) and {releasing_staff} (covering)!")
                else:
                    st.success(f"✅ Change saved for {released_staff}. Note: {releasing_staff} already has a change today.")
            else:
                st.success("✅ Program change saved successfully!")
            
            st.session_state.num_blocks = 1
            st.rerun()

# Display existing changes
st.markdown("---")
st.subheader(f"Program Changes for {target_date.strftime('%A, %d %B %Y')}")

if not changes:
    st.info("No program changes scheduled for this day")
else:
    for idx, change in enumerate(changes):
        with st.container():
            st.markdown(f'<div class="change-card">', unsafe_allow_html=True)
            
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"### Change {idx + 1}: {change.get('reason', 'Program Change')}")
            with col2:
                if st.button("🗑️ Delete", key=f"del_{change['id']}", use_container_width=True):
                    delete_program_change(target_date_str, change['id'])
                    st.rerun()
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Staff Member:** {change.get('staff_name', 'N/A')}")
                if change.get('trt_name'):
                    st.markdown(f"**TRT/Acting:** {change.get('trt_name')}")
            with col2:
                if change.get('notes'):
                    st.markdown(f"**Notes:** {change.get('notes')}")
            
            # Display time blocks
            blocks = change.get('time_blocks', [])
            if blocks:
                st.markdown("**Time Changes:**")
                for block in blocks:
                    st.markdown(f"- {format_time(block.get('start_time', ''))} → {format_time(block.get('end_time', ''))}: **{block.get('modified_program', 'N/A')}**")
            
            st.markdown('</div>', unsafe_allow_html=True)

# Action buttons
st.markdown("---")

# Initialize mobile view state
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

# Show mobile view if toggled
if st.session_state.show_mobile_view:
    st.markdown("---")
    st.markdown("### 📱 Mobile View (Screenshot this for forwarding)")
    mobile_html = render_mobile_view(changes, target_date_str)
    components.html(mobile_html, height=600, scrolling=True)
