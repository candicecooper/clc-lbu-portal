import streamlit as st
import os
from pathlib import Path

st.set_page_config(
    page_title="Sexual Health Resources",
    page_icon="💗",
    layout="wide"
)

# Custom CSS matching portal style
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1F4E78;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .subdomain-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid;
        margin-bottom: 1.5rem;
    }
    .subdomain-a { border-left-color: #ff0000; }
    .subdomain-b { border-left-color: #7030A0; }
    .subdomain-c { border-left-color: #ff3366; }
    .card-title {
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        margin: 0.25rem;
        border-radius: 15px;
        font-size: 0.85rem;
        background: rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">💗 Sexual Health Education Resources</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Curriculum-Aligned | Context-Specific | Ready to Use</div>', unsafe_allow_html=True)

# Overview
with st.expander("ℹ️ About These Resources", expanded=False):
    st.markdown("""
    **Complete resource package for CLC-LBU sexual health education**
    
    - ✅ Australian Curriculum HPE Years 7-10 aligned
    - ✅ Three subdomains for different student profiles
    - ✅ 6 AC focus areas per subdomain
    - ✅ Short (8-15 min) engaging activities
    - ✅ Movement & debate-based (no worksheets)
    - ✅ Trauma-informed approach
    - ✅ Screen-ready presentation slides
    - ✅ Real-world scenarios & consequences
    
    **How to Use:**
    1. Choose subdomain based on student group
    2. Launch slides for visual presentation
    3. Use activity bank document for facilitation
    4. Download additional resources as needed
    """)

# Hub Access Section
st.markdown("---")
st.markdown("## 🏠 Central Hub & Interactive Slides")

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("""
    The **Sexual Health Hub** provides one-click access to all presentation slides and resources.
    Open it in a new browser tab to:
    - Launch full-screen interactive slides
    - Access all subdomain presentations
    - Download activity banks
    - View quick-start guide
    """)

with col2:
    # Hub file path - adjust based on where you upload it
    hub_path = "sexual_health_hub.html"
    if os.path.exists(hub_path):
        with open(hub_path, 'rb') as f:
            st.download_button(
                label="📥 Download Hub Page",
                data=f,
                file_name="sexual_health_hub.html",
                mime="text/html",
                use_container_width=True
            )
    
    st.info("**Tip:** Open hub in full browser window, then press F11 for full-screen presentations")

# Subdomain Cards
st.markdown("---")
st.markdown("## 📚 Resources by Subdomain")

# Helper function to create download button for files
def create_download_button(file_path, label, key):
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            return st.download_button(
                label=label,
                data=f,
                file_name=os.path.basename(file_path),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key=key,
                use_container_width=True
            )
    else:
        st.warning(f"File not found: {file_path}")
        return None

# SUBDOMAIN A
st.markdown("""
<div class="subdomain-card subdomain-a">
    <div class="card-title" style="color: #cc0000;">SUBDOMAIN A: Real Strength vs Needing to Prove It</div>
    <span class="badge">Males 13-15</span>
    <span class="badge">Fighting/Violence</span>
    <span class="badge">Shopping Centres</span>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    if os.path.exists("subdomain_a_slides.html"):
        with open("subdomain_a_slides.html", 'rb') as f:
            st.download_button(
                "🎬 Download Slides (Red)",
                data=f,
                file_name="subdomain_a_slides.html",
                mime="text/html",
                key="slides_a"
            )
with col2:
    create_download_button(
        "Subdomain_A_Males_Fighting_Violence.docx",
        "📄 Activity Bank (Partial)",
        "doc_a"
    )
with col3:
    st.markdown("**Scenarios:** Fighting over girls/disrespect, viral videos, assault charges, brain injury")

st.markdown("<br>", unsafe_allow_html=True)

# SUBDOMAIN B
st.markdown("""
<div class="subdomain-card subdomain-b">
    <div class="card-title" style="color: #7030A0;">SUBDOMAIN B: Street Edition - When "Yes" Isn't Really Yes</div>
    <span class="badge">Males/Females 13-16</span>
    <span class="badge">Drug Users</span>
    <span class="badge">Gang/Street Context</span>
</div>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    if os.path.exists("subdomain_b_slides.html"):
        with open("subdomain_b_slides.html", 'rb') as f:
            st.download_button(
                "🎬 Download Slides (Purple)",
                data=f,
                file_name="subdomain_b_slides.html",
                mime="text/html",
                key="slides_b"
            )
with col2:
    create_download_button(
        "Subdomain_B_Drug_Users_Gang_Street.docx",
        "📄 Activity Bank (Complete)",
        "doc_b1"
    )
with col3:
    create_download_button(
        "Street_Smart_Sexual_Health_Resource_Bank.docx",
        "📄 Street-Smart Resource",
        "doc_b2"
    )
with col4:
    st.markdown("**Scenarios:** Trading sex for drugs, crew pressure, screenshot consequences")

st.markdown("<br>", unsafe_allow_html=True)

# SUBDOMAIN C
st.markdown("""
<div class="subdomain-card subdomain-c">
    <div class="card-title" style="color: #ff3366;">SUBDOMAIN C: Your Body Is Yours</div>
    <span class="badge">Females 13-16</span>
    <span class="badge">Disengaged</span>
    <span class="badge">Vaping/Drugs</span>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    if os.path.exists("subdomain_c_slides.html"):
        with open("subdomain_c_slides.html", 'rb') as f:
            st.download_button(
                "🎬 Download Slides (Pink)",
                data=f,
                file_name="subdomain_c_slides.html",
                mime="text/html",
                key="slides_c"
            )
with col2:
    create_download_button(
        "Subdomain_C_Females_Disengaged_Vaping_Drugs.docx",
        "📄 Activity Bank (Complete)",
        "doc_c"
    )
with col3:
    st.markdown("**Scenarios:** Older boyfriend pressure, image-based abuse, fake friends, reputation")

# Foundation & Additional Resources
st.markdown("---")
st.markdown("## 📖 Foundation & Additional Resources")

tab1, tab2, tab3 = st.tabs(["Framework Documents", "Original Comprehensive Resources", "Focus Area Documents"])

with tab1:
    st.markdown("**Australian Curriculum Framework**")
    col1, col2 = st.columns(2)
    with col1:
        create_download_button(
            "AC_HPE_Framework_and_Subdomain_Strategy.docx",
            "📥 AC HPE Framework & Subdomain Strategy",
            "framework"
        )
    with col2:
        st.markdown("""
        - Maps 6 AC HPE focus areas
        - Explains subdomain differentiation
        - Implementation guidelines
        - Assessment evidence
        """)

with tab2:
    st.markdown("**Original Comprehensive Resources (For mainstream/general use)**")
    col1, col2, col3 = st.columns(3)
    with col1:
        create_download_button(
            "Sexual_Health_Program_Overview.docx",
            "📥 Program Overview",
            "overview"
        )
    with col2:
        create_download_button(
            "Films_and_Media_Resource_Guide.docx",
            "📥 Films & Media Guide",
            "films"
        )
    with col3:
        create_download_button(
            "Film_Study_Activities_and_Questions.docx",
            "📥 Film Study Activities",
            "film_activities"
        )

with tab3:
    st.markdown("**Detailed Focus Area Documents (Original comprehensive approach)**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        create_download_button(
            "Focus_Area_1_Consent_and_Respectful_Relationships.docx",
            "📥 FA1: Consent & Respectful Relationships",
            "fa1"
        )
        create_download_button(
            "Focus_Area_2_Healthy_vs_Unhealthy_Relationships.docx",
            "📥 FA2: Healthy vs Unhealthy Relationships",
            "fa2"
        )
        create_download_button(
            "Focus_Area_3_Bodies_Puberty_Reproduction.docx",
            "📥 FA3: Bodies, Puberty & Reproduction",
            "fa3"
        )
    
    with col2:
        create_download_button(
            "Focus_Area_4_Online_Safety_Image_Based_Abuse.docx",
            "📥 FA4: Online Safety & Image-Based Abuse",
            "fa4"
        )
        create_download_button(
            "Focus_Area_5_Diversity_Inclusion.docx",
            "📥 FA5: Diversity & Inclusion",
            "fa5"
        )
        create_download_button(
            "Focus_Area_6_Rights_Reporting_Getting_Help.docx",
            "📥 FA6: Rights, Reporting & Getting Help",
            "fa6"
        )

# Quick Start Guide
st.markdown("---")
with st.expander("🚀 Quick Start Guide", expanded=False):
    st.markdown("""
    ### For Your First Session
    
    1. **Identify Your Student Group**
       - Males fighting → Subdomain A (Red)
       - Drug users/gang context → Subdomain B (Purple)
       - Disengaged females → Subdomain C (Pink)
    
    2. **Download Resources**
       - Click "Download Slides" for your subdomain
       - Download corresponding Activity Bank document
       - Save hub page for future access
    
    3. **Prepare Presentation**
       - Open slides HTML file in browser (Chrome/Edge/Firefox)
       - Press F11 for full-screen mode
       - Connect laptop to projector/TV
       - Test navigation (arrow keys or click)
    
    4. **Run the Activity**
       - Show title slide as students enter
       - Use Activity Bank document for facilitation notes
       - Display scenario → students move/vote
       - Reveal consequences after discussion
       - End with key message slide
    
    5. **Activities Are Modular**
       - Each activity = 8-15 minutes
       - Mix and match as needed
       - Can run standalone or series
       - No special equipment needed (just screen)
    
    ### Navigation Tips
    - **Arrow keys** (← →) to navigate slides
    - **Spacebar** to advance
    - **ESC** to exit full-screen
    - **Click anywhere** to advance
    - **Home/End keys** to jump to first/last slide
    """)

# Footer
st.markdown("---")
st.caption("💗 CLC-LBU Sexual Health Resources | Australian Curriculum HPE Years 7-10 Aligned | Trauma-Informed Approach")
