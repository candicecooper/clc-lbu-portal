import streamlit as st
from supabase import create_client
import os
from datetime import datetime
import io

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

# Page header
st.title("📋 Committees")
st.markdown("Committee information, meetings, and resources")

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📅 Meetings", "📄 Documents", "⬆️ Upload Document"])

# ========== OVERVIEW TAB ==========
with tab1:
    st.subheader("Committee Structure")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🎯 Key Committees")
        st.markdown("""
        - **Governing Council**
        - **Finance Committee**
        - **Staff Wellbeing Committee**
        - **WHS Committee**
        - **Curriculum Committee**
        """)
    
    with col2:
        st.markdown("### 📋 Quick Links")
        st.markdown("""
        - [DfE Governing Councils](https://www.education.sa.gov.au/parents-and-families/education-sa-leadership/governing-councils)
        - [Committee Guidelines](https://www.education.sa.gov.au/)
        """)
    
    st.divider()
    
    st.markdown("### 📌 Important Information")
    st.info("""
    **Committee Responsibilities:**
    - Provide strategic direction and oversight
    - Review and approve policies
    - Monitor school performance
    - Ensure compliance with regulations
    - Support staff wellbeing and safety
    """)

# ========== MEETINGS TAB ==========
with tab2:
    st.subheader("Committee Meetings")
    
    # You can expand this later with actual meeting scheduling functionality
    st.markdown("### 📅 Upcoming Meetings")
    st.info("Meeting schedule functionality can be added here.")
    
    st.divider()
    
    st.markdown("### 📝 Recent Meeting Minutes")
    st.info("Meeting minutes can be stored and accessed through the Documents tab.")

# ========== DOCUMENTS TAB ==========
with tab3:
    st.subheader("Committee Documents")
    
    # Add filter options
    col1, col2 = st.columns([3, 1])
    with col1:
        search_term = st.text_input("🔍 Search documents", placeholder="Search by name or description...")
    with col2:
        filter_category = st.selectbox("Filter by category", ["All", "Policy", "Procedure", "Meeting Minutes", "Report", "Other"])
    
    try:
        # Fetch all documents from the committees_documents table
        query = supabase.table("committees_documents").select("*").order("upload_date", desc=True)
        
        # Apply category filter
        if filter_category != "All":
            query = query.eq("category", filter_category)
        
        response = query.execute()
        
        if response.data:
            # Filter by search term if provided
            filtered_docs = response.data
            if search_term:
                filtered_docs = [
                    doc for doc in response.data 
                    if search_term.lower() in doc['document_name'].lower() 
                    or (doc.get('description') and search_term.lower() in doc['description'].lower())
                ]
            
            if filtered_docs:
                # Display documents in a clean format
                for doc in filtered_docs:
                    with st.container():
                        col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1.5, 1.5, 1])
                        
                        with col1:
                            st.markdown(f"**{doc['document_name']}**")
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
                            # Download button
                            try:
                                # Get the file from storage
                                file_data = supabase.storage.from_("committees").download(doc['file_path'])
                                
                                st.download_button(
                                    label="⬇️",
                                    data=file_data,
                                    file_name=doc['document_name'],
                                    mime=doc.get('mime_type', 'application/octet-stream'),
                                    key=f"download_{doc['id']}"
                                )
                            except Exception as e:
                                st.error(f"Error: {str(e)[:30]}")
                        
                        st.divider()
            else:
                st.warning(f"No documents found matching '{search_term}'")
        else:
            st.info("📭 No documents uploaded yet. Use the 'Upload Document' tab to add documents.")
    
    except Exception as e:
        st.error(f"Error loading documents: {str(e)}")
        st.info("The database table may need to be created. See setup instructions.")

# ========== UPLOAD TAB ==========
with tab4:
    st.subheader("Upload Committee Document")
    
    with st.form("upload_form"):
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['pdf', 'docx', 'doc', 'xlsx', 'xls', 'pptx', 'txt'],
            help="Supported formats: PDF, Word, Excel, PowerPoint, Text"
        )
        
        # Document details
        col1, col2 = st.columns(2)
        
        with col1:
            doc_name = st.text_input(
                "Document Name*",
                placeholder="e.g., Committees Policy 2026",
                help="Give the document a descriptive name"
            )
            
            category = st.selectbox(
                "Document Category*",
                ["Policy", "Procedure", "Meeting Minutes", "Report", "Other"]
            )
        
        with col2:
            uploaded_by = st.text_input(
                "Your Name*",
                placeholder="e.g., Candice",
                help="Enter your name"
            )
            
            # Add a checkbox for "most recent policy"
            is_current_policy = st.checkbox(
                "📌 Mark as current/active policy",
                help="Check this if this is the most recent version of a policy document"
            )
        
        description = st.text_area(
            "Description (optional)",
            placeholder="Brief description of the document, version notes, or key changes...",
            help="Add any relevant notes about this document"
        )
        
        # Submit button
        submit = st.form_submit_button("📤 Upload Document", use_container_width=True)
        
        if submit:
            if not uploaded_file:
                st.error("Please select a file to upload.")
            elif not doc_name:
                st.error("Please provide a document name.")
            elif not uploaded_by:
                st.error("Please enter your name.")
            else:
                try:
                    # Generate unique file path
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    file_extension = uploaded_file.name.split('.')[-1]
                    file_path = f"{timestamp}_{uploaded_file.name}"
                    
                    # Upload file to Supabase storage
                    file_bytes = uploaded_file.read()
                    
                    storage_response = supabase.storage.from_("committees").upload(
                        file_path,
                        file_bytes,
                        {"content-type": uploaded_file.type}
                    )
                    
                    # Insert metadata into database
                    db_response = supabase.table("committees_documents").insert({
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
                    
                    # Suggest switching to documents tab
                    st.info("📄 Switch to the 'Documents' tab to view your uploaded file.")
                    
                except Exception as e:
                    st.error(f"Error uploading document: {str(e)}")
                    st.info("If this is the first upload, the storage bucket or table may need to be created. See setup instructions.")

# ========== FOOTER ==========
st.divider()
st.caption("💡 Tip: Use the Documents tab to access all committee policies, meeting minutes, and reports in one place.")
