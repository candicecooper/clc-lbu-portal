import streamlit as st
from supabase import create_client
from datetime import datetime

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

# Initialize session state for navigation
if 'committee_view' not in st.session_state:
    st.session_state.committee_view = 'home'

# Navigation handler
def navigate_to(view):
    st.session_state.committee_view = view
    st.rerun()

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
    
    st.markdown("<h3 style='color: #1e3a5f; margin-bottom: 1.5rem;'>Select a committee to view agendas, minutes and action items.</h3>", unsafe_allow_html=True)
    
    # Committee Cards - Row 1
    col1, col2 = st.columns(2)
    
    with col1:
        # PAC Card
        st.markdown("""
            <div style="border: 3px solid #1e3a5f; border-radius: 16px; padding: 2rem; 
                        background: white; margin-bottom: 1.5rem; min-height: 220px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="font-size: 3.5rem; margin-bottom: 1rem;">🏛️</div>
                <h3 style="color: #1e3a5f; margin-bottom: 0.5rem;">Personnel Advisory Committee</h3>
                <p style="color: #64748b; margin-bottom: 1rem;">Agendas · Minutes · Actions</p>
                <span style="background: #d1fae5; color: #065f46; padding: 0.4rem 0.8rem; 
                            border-radius: 20px; font-size: 0.85rem; font-weight: 600;">● Active</span>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Open PAC", key="btn_pac", use_container_width=True):
            navigate_to('pac')
        
        # WHS Card
        st.markdown("""
            <div style="border: 3px solid #ea580c; border-radius: 16px; padding: 2rem; 
                        background: white; margin-bottom: 1.5rem; min-height: 220px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="font-size: 3.5rem; margin-bottom: 1rem;">🦺</div>
                <h3 style="color: #1e3a5f; margin-bottom: 0.5rem;">WHS Committee</h3>
                <p style="color: #64748b; margin-bottom: 1rem;">Safety · Hazards · Compliance</p>
                <span style="background: #fef3c7; color: #92400e; padding: 0.4rem 0.8rem; 
                            border-radius: 20px; font-size: 0.85rem; font-weight: 600;">● Active</span>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Open WHS", key="btn_whs", use_container_width=True):
            navigate_to('whs')
    
    with col2:
        # Finance Card
        st.markdown("""
            <div style="border: 3px solid #059669; border-radius: 16px; padding: 2rem; 
                        background: white; margin-bottom: 1.5rem; min-height: 220px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="font-size: 3.5rem; margin-bottom: 1rem;">💰</div>
                <h3 style="color: #1e3a5f; margin-bottom: 0.5rem;">Finance Committee</h3>
                <p style="color: #64748b; margin-bottom: 1rem;">Budget · Expenditure · Reports</p>
                <span style="background: #d1fae5; color: #065f46; padding: 0.4rem 0.8rem; 
                            border-radius: 20px; font-size: 0.85rem; font-weight: 600;">● Active</span>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Open Finance", key="btn_finance", use_container_width=True):
            navigate_to('finance')
        
        # Social Club Card
        st.markdown("""
            <div style="border: 3px solid #7c3aed; border-radius: 16px; padding: 2rem; 
                        background: white; margin-bottom: 1.5rem; min-height: 220px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="font-size: 3.5rem; margin-bottom: 1rem;">🎉</div>
                <h3 style="color: #1e3a5f; margin-bottom: 0.5rem;">Social Club</h3>
                <p style="color: #64748b; margin-bottom: 1rem;">Events · Activities · Fun</p>
                <span style="background: #e9d5ff; color: #6b21a8; padding: 0.4rem 0.8rem; 
                            border-radius: 20px; font-size: 0.85rem; font-weight: 600;">● Active</span>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Open Social Club", key="btn_social", use_container_width=True):
            navigate_to('social')
    
    # Documents Card - Row 2 (centered)
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
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
        if st.button("📂 Open Documents Library", key="btn_docs", use_container_width=True):
            navigate_to('documents')

# ========== DOCUMENTS VIEW ==========
elif st.session_state.committee_view == 'documents':
    
    # Create tabs for documents functionality
    tab1, tab2 = st.tabs(["📄 View Documents", "⬆️ Upload Document"])
    
    # ========== VIEW DOCUMENTS TAB ==========
    with tab1:
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
                                # Add pin emoji if marked as current
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
    with tab2:
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
                        st.info("📄 Switch to the 'View Documents' tab to see your uploaded file.")
                        
                    except Exception as e:
                        st.error(f"Error uploading document: {str(e)}")
                        st.info("If this is the first upload, the storage bucket or table may need to be created. See setup instructions.")
    
    # Return button
    st.divider()
    if st.button("↩ Return to Committees Home", use_container_width=True):
        navigate_to('home')

# ========== INDIVIDUAL COMMITTEE VIEWS ==========
elif st.session_state.committee_view in ['pac', 'finance', 'whs', 'social']:
    committee_names = {
        'pac': 'Personnel Advisory Committee',
        'finance': 'Finance Committee',
        'whs': 'WHS Committee',
        'social': 'Social Club'
    }
    
    st.info(f"🚧 {committee_names[st.session_state.committee_view]} page - Agendas, minutes, and actions functionality to be implemented.")
    
    if st.button("↩ Return to Committees Home", use_container_width=True):
        navigate_to('home')

# ========== FOOTER ==========
st.divider()
st.caption("💡 Tip: Use the Documents Library to access all committee policies and resources in one place.")
