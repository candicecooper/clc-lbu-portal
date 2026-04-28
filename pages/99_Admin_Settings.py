import streamlit as st
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from auth import require_auth, logout_button, get_staff_name
from database import get_client
from datetime import datetime, date

st.set_page_config(page_title="Admin Settings - CLC Portal", page_icon="⚙️", layout="wide")

# Hide sidebar
st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none;}
    [data-testid="stSidebarNav"] {display: none;}
</style>
""", unsafe_allow_html=True)

require_auth("Admin Settings", "⚙️")
logout_button("sidebar")

st.title("⚙️ Admin Settings")

# Initialize session state
if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = None
if 'show_add_student' not in st.session_state:
    st.session_state.show_add_student = False

# Get Supabase client
supabase = get_client()

# Tab layout
tab1, tab2 = st.tabs(["👥 Manage Students", "🔧 System Settings"])

with tab1:
    st.subheader("Student Records")
    
    # Fetch all students
    try:
        response = supabase.table('students').select('*').order('name').execute()
        students = response.data if response.data else []
    except Exception as e:
        st.error(f"Error loading students: {e}")
        students = []
    
    # Add new student button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ Add New Student", type="primary", use_container_width=True):
            st.session_state.show_add_student = True
            st.session_state.edit_mode = None
            st.rerun()
    
    # Add new student form
    if st.session_state.show_add_student:
        with st.form("add_student_form", clear_on_submit=False):
            st.markdown("### Add New Student")
            
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("Student Name*", key="new_name")
                new_dob = st.date_input("Date of Birth*", value=None, key="new_dob")
                new_program = st.selectbox("Program*", ["JP", "PY", "SY"], key="new_program")
            
            with col2:
                new_start_date = st.date_input("Start Date", value=date.today(), key="new_start_date")
                new_status = st.selectbox("Status", ["Active", "Inactive", "Exited"], key="new_status")
                new_notes = st.text_area("Notes", key="new_notes", height=100)
            
            col1, col2, col3 = st.columns([1, 1, 4])
            with col1:
                submit_new = st.form_submit_button("Save", type="primary", use_container_width=True)
            with col2:
                cancel_new = st.form_submit_button("Cancel", use_container_width=True)
            
            if submit_new:
                if not new_name or not new_dob:
                    st.error("Name and Date of Birth are required")
                else:
                    try:
                        insert_data = {
                            'name': new_name,
                            'dob': new_dob.isoformat(),
                            'program': new_program,
                            'start_date': new_start_date.isoformat(),
                            'status': new_status,
                            'notes': new_notes if new_notes else None
                        }
                        supabase.table('students').insert(insert_data).execute()
                        st.success(f"✅ {new_name} added successfully")
                        st.session_state.show_add_student = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding student: {e}")
            
            if cancel_new:
                st.session_state.show_add_student = False
                st.rerun()
    
    st.divider()
    
    # Display students
    if students:
        st.markdown(f"**Total Students:** {len(students)}")
        
        for student in students:
            student_id = student.get('id')
            
            # Check if this student is in edit mode
            if st.session_state.edit_mode == student_id:
                # Edit mode
                with st.form(f"edit_form_{student_id}", clear_on_submit=False):
                    st.markdown(f"### Editing: {student.get('name')}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        edit_name = st.text_input("Student Name*", value=student.get('name', ''), key=f"edit_name_{student_id}")
                        
                        # Handle DOB
                        current_dob = student.get('dob')
                        if current_dob:
                            if isinstance(current_dob, str):
                                current_dob = datetime.fromisoformat(current_dob.replace('Z', '+00:00')).date()
                        edit_dob = st.date_input("Date of Birth*", value=current_dob, key=f"edit_dob_{student_id}")
                        
                        edit_program = st.selectbox("Program*", ["JP", "PY", "SY"], 
                                                   index=["JP", "PY", "SY"].index(student.get('program', 'JP')), 
                                                   key=f"edit_program_{student_id}")
                    
                    with col2:
                        # Handle start_date
                        current_start = student.get('start_date')
                        if current_start:
                            if isinstance(current_start, str):
                                current_start = datetime.fromisoformat(current_start.replace('Z', '+00:00')).date()
                        edit_start_date = st.date_input("Start Date", value=current_start if current_start else date.today(), 
                                                       key=f"edit_start_{student_id}")
                        
                        edit_status = st.selectbox("Status", ["Active", "Inactive", "Exited"], 
                                                  index=["Active", "Inactive", "Exited"].index(student.get('status', 'Active')),
                                                  key=f"edit_status_{student_id}")
                        edit_notes = st.text_area("Notes", value=student.get('notes', ''), key=f"edit_notes_{student_id}", height=100)
                    
                    col1, col2, col3 = st.columns([1, 1, 4])
                    with col1:
                        submit_edit = st.form_submit_button("💾 Save", type="primary", use_container_width=True)
                    with col2:
                        cancel_edit = st.form_submit_button("Cancel", use_container_width=True)
                    
                    if submit_edit:
                        if not edit_name or not edit_dob:
                            st.error("Name and Date of Birth are required")
                        else:
                            try:
                                update_data = {
                                    'name': edit_name,
                                    'dob': edit_dob.isoformat(),
                                    'program': edit_program,
                                    'start_date': edit_start_date.isoformat(),
                                    'status': edit_status,
                                    'notes': edit_notes if edit_notes else None
                                }
                                supabase.table('students').update(update_data).eq('id', student_id).execute()
                                st.success(f"✅ {edit_name} updated successfully")
                                st.session_state.edit_mode = None
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error updating student: {e}")
                    
                    if cancel_edit:
                        st.session_state.edit_mode = None
                        st.rerun()
                
            else:
                # Display mode
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    
                    with col1:
                        status_emoji = "🟢" if student.get('status') == 'Active' else "🔴" if student.get('status') == 'Exited' else "🟡"
                        st.markdown(f"**{status_emoji} {student.get('name')}**")
                    
                    with col2:
                        dob = student.get('dob')
                        if dob:
                            if isinstance(dob, str):
                                dob_date = datetime.fromisoformat(dob.replace('Z', '+00:00')).date()
                            else:
                                dob_date = dob
                            age = (date.today() - dob_date).days // 365
                            st.text(f"DOB: {dob_date.strftime('%d/%m/%Y')} (Age {age})")
                        else:
                            st.text("DOB: Not set")
                    
                    with col3:
                        st.text(f"Program: {student.get('program', 'N/A')}")
                    
                    with col4:
                        if st.button("✏️", key=f"edit_btn_{student_id}", help="Edit student", use_container_width=True):
                            st.session_state.edit_mode = student_id
                            st.session_state.show_add_student = False
                            st.rerun()
                    
                    # Show additional details if available
                    if student.get('notes'):
                        with st.expander("📝 Notes"):
                            st.text(student.get('notes'))
                    
                    st.divider()
    else:
        st.info("No students found. Click 'Add New Student' to get started.")

with tab2:
    st.subheader("System Settings")
    st.info("System configuration settings will be added here.")
    
    st.markdown("### Database Connection")
    try:
        # Test connection
        test = supabase.table('students').select('id').limit(1).execute()
        st.success("✅ Supabase connection active")
    except Exception as e:
        st.error(f"❌ Database connection error: {e}")
