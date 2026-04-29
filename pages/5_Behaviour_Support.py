import streamlit as st
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from auth import require_auth, logout_button, get_staff_name
from database import get_client
from datetime import datetime, date, time, timedelta
import json
import os
import requests
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="Behaviour Support - CLC Portal", page_icon="🎯", layout="wide")

# Hide sidebar
st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none;}
    [data-testid="stSidebarNav"] {display: none;}
</style>
""", unsafe_allow_html=True)

require_auth("Behaviour Support", "🎯")
logout_button("sidebar")

# Check for Quick Incident Log mode
query_params = st.query_params
quick_mode = query_params.get("mode") == "quicklog"

# Initialize session state
if 'incidents' not in st.session_state:
    st.session_state.incidents = []
if 'current_student' not in st.session_state:
    st.session_state.current_student = None

# Get Supabase client
supabase = get_client()

# Behaviour type canonical labels
BEHAVIOUR_TYPES = [
    "Physical aggression toward peers",
    "Physical aggression toward staff",
    "Property damage",
    "Self-harm",
    "Verbal aggression/threats",
    "Refusal/non-compliance",
    "Elopement/wandering",
    "Inappropriate sexual behaviour",
    "Substance use",
    "Disruptive behaviour",
    "Withdrawal/shutdown",
    "Emotional dysregulation",
    "Sensory-seeking behaviour",
    "Other"
]

# Window of Tolerance zones with correct clinical colors
WOT_ZONES = {
    "Green Zone - Regulated": {
        "color": "#7CB342",  # Green
        "description": "Calm, focused, able to learn and engage"
    },
    "Yellow Zone - Hyper-arousal": {
        "color": "#FFB300",  # Amber/Yellow
        "description": "Anxious, irritable, elevated energy, difficulty concentrating"
    },
    "Red Zone - Hypo-arousal": {
        "color": "#E53935",  # Red
        "description": "Shutdown, withdrawn, disconnected, frozen"
    }
}

def get_groq_response(prompt, system_message="You are a helpful assistant."):
    """Get response from Groq AI"""
    try:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return None
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 4000
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        return result['choices'][0]['message']['content']
    
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

def extract_incidents_from_text(text_input):
    """Extract incidents from pasted or uploaded historical data using AI"""
    
    # Fixed f-string with doubled curly braces for JSON template
    system_message = """You are a behaviour analysis expert. Extract incident data from text and return ONLY valid JSON array format. Be precise and clinical."""
    
    prompt = f"""Extract all behaviour incidents from the following text. Return ONLY a JSON array with this exact structure (no markdown, no explanation):

[
  {{{{
    "date": "YYYY-MM-DD",
    "time": "HH:MM",
    "location": "location description",
    "context": "what was happening before the incident",
    "behaviour": "detailed narrative of what the student did",
    "behaviour_type": "select ONE from this list: {', '.join(BEHAVIOUR_TYPES)}",
    "consequence": "what staff did in response",
    "duration_minutes": number or null,
    "severity": "Low/Medium/High",
    "window_zone": "Green Zone - Regulated/Yellow Zone - Hyper-arousal/Red Zone - Hypo-arousal"
  }}}}
]

CRITICAL RULES:
- Return ONLY the JSON array, no other text
- Use exact behaviour_type labels from the list provided
- If date/time unclear, estimate based on context
- Map emotional state to window_zone: calm=Green, anxious/agitated=Yellow, shutdown/withdrawn=Red
- Every incident must have all fields

TEXT TO ANALYZE:
{text_input}"""

    response = get_groq_response(prompt, system_message)
    
    if not response:
        return None
    
    try:
        # Clean response - remove markdown code blocks if present
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()
        
        # Parse JSON
        incidents = json.loads(cleaned)
        
        if not isinstance(incidents, list):
            return None
        
        # Validate and clean each incident
        validated = []
        for inc in incidents:
            if all(k in inc for k in ['date', 'behaviour', 'behaviour_type']):
                # Ensure behaviour_type is valid
                if inc['behaviour_type'] not in BEHAVIOUR_TYPES:
                    inc['behaviour_type'] = 'Other'
                
                # Ensure window_zone is valid
                valid_zones = list(WOT_ZONES.keys())
                if 'window_zone' not in inc or inc['window_zone'] not in valid_zones:
                    inc['window_zone'] = 'Yellow Zone - Hyper-arousal'
                
                validated.append(inc)
        
        return validated if validated else None
    
    except json.JSONDecodeError as e:
        st.error(f"JSON parsing error: {e}")
        return None
    except Exception as e:
        st.error(f"Extraction error: {e}")
        return None

def generate_bap_document(student_name, incidents_data, analysis_text=""):
    """Generate Behaviour Analysis Plan Word document"""
    
    doc = Document()
    
    # Header
    header = doc.sections[0].header
    header_para = header.paragraphs[0]
    header_para.text = "Cowandilla Learning Centre - Learning and Behaviour Unit"
    header_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    header_para.runs[0].font.size = Pt(10)
    header_para.runs[0].font.color.rgb = RGBColor(26, 122, 110)  # Teal
    
    # Title
    title = doc.add_heading(f"Behaviour Analysis Plan", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Student details
    doc.add_paragraph(f"Student: {student_name}")
    doc.add_paragraph(f"Report Date: {date.today().strftime('%d/%m/%Y')}")
    doc.add_paragraph(f"Reporting Period: {len(incidents_data)} incidents analyzed")
    
    doc.add_paragraph()
    
    # Analysis summary
    if analysis_text:
        doc.add_heading("Behaviour Analysis Summary", 1)
        doc.add_paragraph(analysis_text)
    
    # Incident table
    doc.add_heading("Incident Log", 1)
    
    if incidents_data:
        table = doc.add_table(rows=1, cols=6)
        table.style = 'Light Grid Accent 1'
        
        # Header row
        headers = ['Date/Time', 'Location', 'Behaviour Type', 'Severity', 'Zone', 'Description']
        for i, header in enumerate(headers):
            cell = table.rows[0].cells[i]
            cell.text = header
            cell.paragraphs[0].runs[0].bold = True
        
        # Data rows
        for inc in incidents_data:
            row = table.add_row()
            row.cells[0].text = f"{inc.get('date', 'N/A')} {inc.get('time', '')}"
            row.cells[1].text = inc.get('location', 'N/A')
            row.cells[2].text = inc.get('behaviour_type', 'N/A')
            row.cells[3].text = inc.get('severity', 'N/A')
            row.cells[4].text = inc.get('window_zone', 'N/A').split(' - ')[0]  # Just zone color
            row.cells[5].text = inc.get('behaviour', 'N/A')[:100]  # Truncate for table
    
    # Save to BytesIO
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    return buffer

def render_quick_incident_log():
    """Quick incident logging interface"""
    st.title("⚡ Quick Incident Log")
    st.caption("Fast incident entry - opens from any page via ?mode=quicklog")
    
    with st.form("quick_incident_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            student_name = st.text_input("Student Name*", key="quick_student")
            incident_date = st.date_input("Date*", value=date.today(), key="quick_date")
            incident_time = st.time_input("Time*", value=datetime.now().time(), key="quick_time")
        
        with col2:
            location = st.text_input("Location*", key="quick_location")
            behaviour_type = st.selectbox("Behaviour Type*", BEHAVIOUR_TYPES, key="quick_type")
            severity = st.selectbox("Severity*", ["Low", "Medium", "High"], index=1, key="quick_severity")
        
        context = st.text_area("Context/Antecedent", key="quick_context", height=80)
        behaviour = st.text_area("Behaviour Description*", key="quick_behaviour", height=100)
        consequence = st.text_area("Staff Response", key="quick_consequence", height=80)
        
        col1, col2, col3 = st.columns([1, 1, 3])
        
        with col1:
            submit = st.form_submit_button("💾 Log Incident", type="primary", use_container_width=True)
        with col2:
            if st.form_submit_button("Cancel", use_container_width=True):
                st.switch_page("pages/1_Daily_Bulletin.py")
        
        if submit:
            if not all([student_name, incident_date, incident_time, location, behaviour_type, behaviour]):
                st.error("Please fill all required fields (marked with *)")
            else:
                try:
                    incident_data = {
                        'student_name': student_name,
                        'incident_date': incident_date.isoformat(),
                        'incident_time': incident_time.strftime('%H:%M'),
                        'location': location,
                        'context': context if context else None,
                        'behaviour': behaviour,
                        'behaviour_type': behaviour_type,
                        'consequence': consequence if consequence else None,
                        'severity': severity,
                        'window_zone': 'Yellow Zone - Hyper-arousal',  # Default
                        'logged_by': get_staff_name(),
                        'logged_at': datetime.now().isoformat()
                    }
                    
                    supabase.table('behaviour_incidents').insert(incident_data).execute()
                    st.success(f"✅ Incident logged for {student_name}")
                    st.balloons()
                    
                    # Auto-close after 2 seconds
                    import time
                    time.sleep(2)
                    st.switch_page("pages/1_Daily_Bulletin.py")
                    
                except Exception as e:
                    st.error(f"Error logging incident: {e}")

def render_main_interface():
    """Main behaviour support interface"""
    st.title("🎯 Behaviour Support Tool")
    
    # Fetch students (exclude archived)
    try:
        response = supabase.table('students').select('*').eq('status', 'Active').order('name').execute()
        # Filter out archived students (some have archived=true, some don't have the field)
        students = [s for s in (response.data or []) if not s.get('archived', False)]
    except Exception as e:
        st.error(f"Error loading students: {e}")
        students = []
    
    # Student selection
    if students:
        student_names = [s['name'] for s in students]
        selected_name = st.selectbox("Select Student", [""] + student_names, key="student_select")
        
        if selected_name:
            st.session_state.current_student = selected_name
            selected_student = next((s for s in students if s['name'] == selected_name), None)
        else:
            st.session_state.current_student = None
            selected_student = None
    else:
        st.warning("No active students found. Add students in Admin Settings.")
        selected_student = None
        st.session_state.current_student = None
    
    if not st.session_state.current_student:
        st.info("👆 Select a student to begin")
        return
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 Log Incident", 
        "📊 Analysis & Reports",
        "📈 Visual Analytics",
        "🧠 Sensory Overview",
        "📚 Historical Import"
    ])
    
    with tab1:
        render_incident_log_tab(selected_student)
    
    with tab2:
        render_analysis_tab(selected_student)
    
    with tab3:
        render_analytics_tab(selected_student)
    
    with tab4:
        render_sensory_tab(selected_student)
    
    with tab5:
        render_historical_import_tab()

def render_incident_log_tab(student):
    """Incident logging interface"""
    st.subheader(f"Log Incident for {student['name']}")
    
    with st.form("incident_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            incident_date = st.date_input("Date*", value=date.today())
        with col2:
            incident_time = st.time_input("Time*", value=datetime.now().time())
        with col3:
            duration = st.number_input("Duration (minutes)", min_value=0, value=5)
        
        col1, col2 = st.columns(2)
        
        with col1:
            location = st.text_input("Location*", placeholder="e.g., Classroom, Yard, Office")
            behaviour_type = st.selectbox("Behaviour Type*", BEHAVIOUR_TYPES)
        
        with col2:
            severity = st.select_slider("Severity*", options=["Low", "Medium", "High"], value="Medium")
            window_zone = st.selectbox("Window of Tolerance Zone*", list(WOT_ZONES.keys()))
        
        # Show zone description
        if window_zone:
            zone_info = WOT_ZONES[window_zone]
            st.info(f"**{window_zone}**: {zone_info['description']}")
        
        context = st.text_area("Context/Antecedent*", 
                              placeholder="What was happening before the incident? Triggers, activities, interactions...",
                              height=100)
        
        behaviour = st.text_area("Behaviour Description*", 
                                placeholder="Detailed narrative of what happened...",
                                height=150)
        
        consequence = st.text_area("Staff Response/Consequence*", 
                                  placeholder="What did staff do? De-escalation strategies, supports provided...",
                                  height=100)
        
        col1, col2, col3 = st.columns([1, 1, 4])
        
        with col1:
            submit = st.form_submit_button("💾 Save Incident", type="primary", use_container_width=True)
        with col2:
            clear = st.form_submit_button("Clear", use_container_width=True)
        
        if submit:
            if not all([incident_date, incident_time, location, behaviour_type, context, behaviour, consequence]):
                st.error("Please fill all required fields (marked with *)")
            else:
                try:
                    incident_data = {
                        'student_id': student['id'],
                        'student_name': student['name'],
                        'incident_date': incident_date.isoformat(),
                        'incident_time': incident_time.strftime('%H:%M'),
                        'duration_minutes': duration if duration > 0 else None,
                        'location': location,
                        'context': context,
                        'behaviour': behaviour,
                        'behaviour_type': behaviour_type,
                        'consequence': consequence,
                        'severity': severity,
                        'window_zone': window_zone,
                        'logged_by': get_staff_name(),
                        'logged_at': datetime.now().isoformat()
                    }
                    
                    supabase.table('behaviour_incidents').insert(incident_data).execute()
                    st.success("✅ Incident logged successfully")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"Error logging incident: {e}")

def render_analysis_tab(student):
    """Analysis and report generation"""
    st.subheader(f"Analysis for {student['name']}")
    
    # Fetch incidents
    try:
        response = supabase.table('behaviour_incidents')\
            .select('*')\
            .eq('student_id', student['id'])\
            .order('incident_date', desc=True)\
            .order('incident_time', desc=True)\
            .execute()
        
        incidents = response.data if response.data else []
    except Exception as e:
        st.error(f"Error loading incidents: {e}")
        incidents = []
    
    if not incidents:
        st.info("No incidents recorded yet. Log incidents in the first tab.")
        return
    
    st.metric("Total Incidents", len(incidents))
    
    # Date range filter
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("From", value=date.today() - timedelta(days=30))
    with col2:
        end_date = st.date_input("To", value=date.today())
    
    # Filter incidents by date
    filtered = [
        inc for inc in incidents 
        if start_date <= datetime.fromisoformat(inc['incident_date']).date() <= end_date
    ]
    
    st.markdown(f"**Showing {len(filtered)} incidents** in selected range")
    
    # Summary stats
    if filtered:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            severity_counts = {}
            for inc in filtered:
                sev = inc.get('severity', 'Unknown')
                severity_counts[sev] = severity_counts.get(sev, 0) + 1
            st.markdown("**Severity Breakdown:**")
            for sev, count in severity_counts.items():
                st.text(f"{sev}: {count}")
        
        with col2:
            type_counts = {}
            for inc in filtered:
                btype = inc.get('behaviour_type', 'Unknown')
                type_counts[btype] = type_counts.get(btype, 0) + 1
            top_type = max(type_counts.items(), key=lambda x: x[1]) if type_counts else ('N/A', 0)
            st.metric("Most Common Behaviour", top_type[0], f"{top_type[1]} incidents")
        
        with col3:
            zone_counts = {}
            for inc in filtered:
                zone = inc.get('window_zone', 'Unknown')
                zone_counts[zone] = zone_counts.get(zone, 0) + 1
            st.markdown("**Window of Tolerance:**")
            for zone, count in zone_counts.items():
                zone_color = zone.split(' - ')[0]
                st.text(f"{zone_color}: {count}")
    
    # Generate BAP button
    st.divider()
    
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("📄 Generate BAP Document", type="primary", use_container_width=True):
            with st.spinner("Generating document..."):
                doc_buffer = generate_bap_document(student['name'], filtered)
                filename = f"BAP_{student['name'].replace(' ', '_')}_{date.today().isoformat()}.docx"
                
                st.download_button(
                    label="⬇️ Download BAP",
                    data=doc_buffer,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )

def render_analytics_tab(student):
    """Visual analytics and charts"""
    st.subheader(f"Analytics for {student['name']}")
    
    # Fetch incidents
    try:
        response = supabase.table('behaviour_incidents')\
            .select('*')\
            .eq('student_id', student['id'])\
            .order('incident_date')\
            .execute()
        
        incidents = response.data if response.data else []
    except Exception as e:
        st.error(f"Error loading incidents: {e}")
        incidents = []
    
    if not incidents:
        st.info("No data to visualize yet.")
        return
    
    # Prepare dataframe
    df = pd.DataFrame(incidents)
    df['incident_date'] = pd.to_datetime(df['incident_date'])
    df['incident_datetime'] = pd.to_datetime(
        df['incident_date'].astype(str) + ' ' + df['incident_time'].astype(str)
    )
    
    # Incidents over time
    st.markdown("### Incidents Over Time")
    daily_counts = df.groupby(df['incident_date'].dt.date).size().reset_index()
    daily_counts.columns = ['date', 'count']
    
    fig_timeline = px.line(daily_counts, x='date', y='count', 
                          title='Daily Incident Frequency',
                          markers=True)
    fig_timeline.update_layout(xaxis_title='Date', yaxis_title='Number of Incidents')
    st.plotly_chart(fig_timeline, use_container_width=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Behaviour type distribution
        st.markdown("### Behaviour Types")
        type_counts = df['behaviour_type'].value_counts()
        fig_types = px.pie(values=type_counts.values, names=type_counts.index,
                          title='Distribution by Type')
        st.plotly_chart(fig_types, use_container_width=True)
    
    with col2:
        # Window of Tolerance distribution
        st.markdown("### Window of Tolerance Zones")
        zone_counts = df['window_zone'].value_counts()
        
        # Map to colors
        color_map = {zone: WOT_ZONES[zone]['color'] for zone in WOT_ZONES.keys()}
        colors = [color_map.get(zone, '#999999') for zone in zone_counts.index]
        
        fig_zones = go.Figure(data=[go.Pie(
            labels=zone_counts.index,
            values=zone_counts.values,
            marker=dict(colors=colors),
            hole=.3
        )])
        fig_zones.update_layout(title='Regulation Zones')
        st.plotly_chart(fig_zones, use_container_width=True)
    
    # Severity chart
    st.markdown("### Severity Distribution")
    severity_counts = df['severity'].value_counts()
    severity_order = ['Low', 'Medium', 'High']
    severity_counts = severity_counts.reindex(severity_order, fill_value=0)
    
    severity_colors = {'Low': '#7CB342', 'Medium': '#FFB300', 'High': '#E53935'}
    colors = [severity_colors[sev] for sev in severity_counts.index]
    
    fig_severity = go.Figure(data=[
        go.Bar(x=severity_counts.index, y=severity_counts.values,
              marker_color=colors)
    ])
    fig_severity.update_layout(title='Incident Severity',
                              xaxis_title='Severity Level',
                              yaxis_title='Count')
    st.plotly_chart(fig_severity, use_container_width=True)

def render_sensory_tab(student):
    """Sensory overview integration"""
    st.subheader(f"Sensory Profile for {student['name']}")
    
    st.info("🧠 Sensory profiles can be created in the dedicated Sensory Overview tool")
    
    # Try to fetch sensory data
    try:
        response = supabase.table('sensory_profiles')\
            .select('*')\
            .eq('student_id', student['id'])\
            .order('created_at', desc=True)\
            .limit(1)\
            .execute()
        
        if response.data:
            profile = response.data[0]
            st.success("✅ Sensory profile found")
            
            with st.expander("View Sensory Profile Details"):
                st.json(profile)
        else:
            st.warning("No sensory profile found for this student")
            
    except Exception as e:
        st.caption(f"Sensory data not available: {e}")

def render_historical_import_tab():
    """Historical data import via paste or upload"""
    st.subheader("📚 Import Historical Incidents")
    st.caption("Paste or upload historical incident data - AI will extract and structure it")
    
    import_method = st.radio("Import Method", ["Paste Text", "Upload File"], horizontal=True)
    
    historical_text = ""
    
    if import_method == "Paste Text":
        historical_text = st.text_area(
            "Paste historical incident records",
            height=300,
            placeholder="Paste incident logs, emails, notes, or any text containing incident information..."
        )
    else:
        uploaded_file = st.file_uploader("Upload file", type=['txt', 'docx', 'pdf'])
        
        if uploaded_file:
            if uploaded_file.type == 'text/plain':
                historical_text = uploaded_file.read().decode('utf-8')
                st.success(f"✅ Loaded {len(historical_text)} characters from {uploaded_file.name}")
            elif uploaded_file.type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                doc = Document(BytesIO(uploaded_file.read()))
                historical_text = '\n'.join([para.text for para in doc.paragraphs])
                st.success(f"✅ Extracted text from {uploaded_file.name}")
            else:
                st.error("PDF upload support coming soon. Please use .txt or .docx for now.")
    
    if historical_text and st.button("🤖 Extract Incidents with AI", type="primary"):
        with st.spinner("Analyzing text and extracting incidents..."):
            extracted = extract_incidents_from_text(historical_text)
            
            if extracted:
                st.success(f"✅ Extracted {len(extracted)} incidents")
                
                st.markdown("### Review Extracted Incidents")
                st.caption("Review below and edit if needed before saving to database")
                
                # Display as editable JSON
                edited_json = st.text_area(
                    "Extracted Data (JSON)",
                    value=json.dumps(extracted, indent=2),
                    height=400
                )
                
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("💾 Save All to Database", type="primary", use_container_width=True):
                        try:
                            incidents_to_save = json.loads(edited_json)
                            
                            # Add metadata and save each
                            saved_count = 0
                            for inc in incidents_to_save:
                                inc['student_name'] = st.session_state.current_student
                                inc['logged_by'] = f"{get_staff_name()} (imported)"
                                inc['logged_at'] = datetime.now().isoformat()
                                
                                # Get student_id if possible
                                if st.session_state.current_student:
                                    try:
                                        student_response = supabase.table('students')\
                                            .select('id')\
                                            .eq('name', st.session_state.current_student)\
                                            .execute()
                                        if student_response.data:
                                            inc['student_id'] = student_response.data[0]['id']
                                    except:
                                        pass
                                
                                supabase.table('behaviour_incidents').insert(inc).execute()
                                saved_count += 1
                            
                            st.success(f"✅ Saved {saved_count} incidents to database")
                            st.balloons()
                            
                        except json.JSONDecodeError:
                            st.error("Invalid JSON format. Please check the data.")
                        except Exception as e:
                            st.error(f"Error saving incidents: {e}")
            else:
                st.error("❌ AI extraction failed. Please check the format and try again.")
                st.info("💡 Try including clearer date/time information and behaviour descriptions")

# Main routing
if quick_mode:
    render_quick_incident_log()
else:
    render_main_interface()
