import streamlit as st
from datetime import datetime, date, time
import pandas as pd
from supabase import create_client
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io

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

# Initialize Supabase - Direct connection to bypass schema cache issues
supabase = create_client(
    st.secrets["supabase"]["url"],
    st.secrets["supabase"]["key"]
)

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

def get_todays_changes():
    """Get program changes for today"""
    today = date.today().isoformat()
    response = supabase.table("program_changes").select("*").eq("change_date", today).order("created_at").execute()
    return response.data if response.data else []

def save_program_change(change_data):
    """Save a program change to database"""
    response = supabase.table("program_changes").insert(change_data).execute()
    return response.data

def delete_program_change(change_id):
    """Delete a program change"""
    response = supabase.table("program_changes").delete().eq("id", change_id).execute()
    return response.data

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
    """Render mobile-friendly view"""
    date_str = datetime.strptime(target_date, '%Y-%m-%d').strftime('%A, %d %B %Y')
    
    html = f"""
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
                html += f'<div style="font-size: 0.85rem; color: #666;">TRT: {change.get("trt_name")}</div>'
            
            blocks = change.get('time_blocks', [])
            if blocks:
                html += '<div class="mobile-blocks">'
                for block in blocks:
                    start = format_time(block.get('start_time', ''))
                    end = format_time(block.get('end_time', ''))
                    program = block.get('modified_program', 'N/A')
                    html += f'<div><span class="mobile-time">{start} → {end}</span>: {program}</div>'
                html += '</div>'
            
            html += '</div>'
    
    html += '</div>'
    return html

# Main interface
st.title("📋 Program Changes Manager")

# Check for mobile or PDF mode
query_params = st.query_params
mode = query_params.get("mode", None)

# Date selector
col1, col2 = st.columns([3, 1])
with col1:
    target_date = st.date_input("Select Date", value=date.today(), key="target_date")
with col2:
    st.write("")
    st.write("")
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

target_date_str = target_date.isoformat()

# Get existing changes
existing_changes = supabase.table("program_changes").select("*").eq("change_date", target_date_str).order("created_at").execute()
changes = existing_changes.data if existing_changes.data else []

# Mode handling
if mode == "mobile":
    st.markdown(render_mobile_view(changes, target_date_str), unsafe_allow_html=True)
    st.stop()

# Main interface continues
st.markdown("---")

# Add new change section
with st.expander("➕ Add New Program Change", expanded=len(changes) == 0):
    with st.form("new_change_form"):
        st.subheader("Change Details")
        
        col1, col2 = st.columns(2)
        with col1:
            staff_name = st.text_input("Staff Member *", placeholder="e.g., Ben Sutton")
            reason = st.text_input("Reason for Change *", placeholder="e.g., Professional Learning, Sick Leave")
        with col2:
            trt_name = st.text_input("TRT/Acting (if applicable)", placeholder="e.g., Gary")
            notes = st.text_area("Additional Notes", placeholder="Optional notes...")
        
        st.subheader("Time Blocks")
        st.caption("Add the time periods affected and what the modified program is")
        
        # Dynamic time blocks
        if 'num_blocks' not in st.session_state:
            st.session_state.num_blocks = 1
        
        time_blocks = []
        for i in range(st.session_state.num_blocks):
            st.markdown(f"**Block {i + 1}**")
            bcol1, bcol2, bcol3 = st.columns([2, 2, 3])
            with bcol1:
                start_time = st.time_input(f"Start Time", value=time(9, 0), key=f"start_{i}")
            with bcol2:
                end_time = st.time_input(f"End Time", value=time(10, 0), key=f"end_{i}")
            with bcol3:
                modified_program = st.text_input(f"Modified Program", placeholder="e.g., TRT, PRT, Meeting", key=f"program_{i}")
            
            time_blocks.append({
                'start_time': start_time.strftime("%H:%M:%S"),
                'end_time': end_time.strftime("%H:%M:%S"),
                'modified_program': modified_program
            })
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.form_submit_button("➕ Add Block"):
                st.session_state.num_blocks += 1
                st.rerun()
        
        st.markdown("---")
        submitted = st.form_submit_button("💾 Save Program Change", type="primary", use_container_width=True)
        
        if submitted:
            if not staff_name or not reason:
                st.error("Please fill in Staff Member and Reason")
            else:
                # Filter out empty blocks
                valid_blocks = [b for b in time_blocks if b['modified_program']]
                
                change_data = {
                    'change_date': target_date_str,
                    'staff_name': staff_name,
                    'reason': reason,
                    'trt_name': trt_name if trt_name else None,
                    'notes': notes if notes else None,
                    'time_blocks': valid_blocks,
                    'created_at': datetime.now().isoformat()
                }
                
                save_program_change(change_data)
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
                    delete_program_change(change['id'])
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
col1, col2 = st.columns(2)

with col1:
    if st.button("📱 Mobile View", use_container_width=True, type="secondary"):
        st.switch_page(f"pages/29_Program_Changes_Manager.py?mode=mobile&date={target_date_str}")

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

# Mobile view display (when in mobile mode)
if mode == "mobile":
    st.markdown(render_mobile_view(changes, target_date_str), unsafe_allow_html=True)
