"""
CLC Safety & Risk Plan Builder - CHECKPOINT VERSION
====================================================

COMPLETELY REDESIGNED WORKFLOW:
- Save after EVERY step (no long sessions)
- Work on ONE risk at a time
- Generate Word doc after each risk (can resume later)
- Upload previous checkpoint to continue
- No data loss - everything saved to files

NEW WORKFLOW:
1. Enter student details → Save checkpoint
2. Add ONE risk → Generate partial document
3. Add another risk → Generate updated document
4. Repeat until done
5. Generate final formatted plan

FEATURES:
✓ Save checkpoint after every action
✓ Resume from any checkpoint
✓ Generate partial documents as you go
✓ No long sessions = no timeouts
✓ Each risk saved individually

"""

import streamlit as st
from groq import Groq
import json, os, io, time
from datetime import date, datetime
from copy import deepcopy
import base64

from docx import Document as DocxDocument
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

# ── Colours ────────────────────────────────────────────────────────────────────
TEAL = "#1A7A6E"

# ══════════════════════════════════════════════════════════════════════════════
# CHECKPOINT SAVE/LOAD FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def create_checkpoint():
    """Create downloadable checkpoint file with current progress"""
    checkpoint_data = {
        "timestamp": datetime.now().isoformat(),
        "student": st.session_state.student,
        "risks": st.session_state.risks,
        "priority_actions": st.session_state.get('priority_actions', ''),
        "review_date": st.session_state.get('review_date', ''),
        "version": "checkpoint_v1"
    }
    return json.dumps(checkpoint_data, indent=2)

def load_checkpoint(checkpoint_file):
    """Load checkpoint and restore session state"""
    try:
        data = json.load(checkpoint_file)
        st.session_state.student = data.get('student', {})
        st.session_state.risks = data.get('risks', [])
        st.session_state.priority_actions = data.get('priority_actions', '')
        st.session_state.review_date = data.get('review_date', '')
        return True, "Checkpoint loaded successfully"
    except Exception as e:
        return False, f"Error loading checkpoint: {str(e)}"

def create_partial_document():
    """Generate Word document with current progress"""
    doc = DocxDocument()
    
    # Title
    title = doc.add_heading('Safety & Risk Management Plan (DRAFT)', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Student details
    student = st.session_state.student
    doc.add_heading('Student Details', 1)
    p = doc.add_paragraph()
    p.add_run('Name: ').bold = True
    p.add_run(f"{student.get('name', 'N/A')}\n")
    p.add_run('DOB: ').bold = True
    p.add_run(f"{student.get('dob', 'N/A')}\n")
    p.add_run('EDSAS: ').bold = True
    p.add_run(f"{student.get('edsas', 'N/A')}\n")
    p.add_run('Program: ').bold = True
    p.add_run(f"{student.get('program', 'N/A')}\n")
    p.add_run('Home School: ').bold = True
    p.add_run(f"{student.get('home_school', 'N/A')}\n")
    
    # Risks
    doc.add_heading('Risk Areas', 1)
    risks = st.session_state.risks
    
    if not risks:
        doc.add_paragraph('No risks added yet.')
    else:
        for i, risk in enumerate(risks, 1):
            doc.add_heading(f"Risk {i}: {risk.get('issue_title', 'Untitled')}", 2)
            
            # Issue detail
            doc.add_paragraph().add_run('Behaviour Description:').bold = True
            doc.add_paragraph(risk.get('issue_detail', 'N/A'))
            
            # Descriptors
            if risk.get('behaviour_descriptors'):
                doc.add_paragraph().add_run('Specific Descriptors:').bold = True
                doc.add_paragraph(risk.get('behaviour_descriptors', ''))
            
            # Risk rating
            doc.add_paragraph().add_run('Risk Rating:').bold = True
            doc.add_paragraph(f"Likelihood: {risk.get('likelihood', 'N/A')}")
            doc.add_paragraph(f"Consequence: {risk.get('consequence', 'N/A')}")
            
            # Strategies
            if risk.get('proactive'):
                doc.add_paragraph().add_run('Proactive Strategies:').bold = True
                doc.add_paragraph(risk.get('proactive', 'Not yet added'))
            
            if risk.get('procedure'):
                doc.add_paragraph().add_run('Reactive Procedures:').bold = True
                doc.add_paragraph(risk.get('procedure', 'Not yet added'))
            
            doc.add_paragraph()  # Spacing
    
    # Priority actions
    if st.session_state.get('priority_actions'):
        doc.add_heading('Priority Actions', 1)
        doc.add_paragraph(st.session_state.priority_actions)
    
    # Footer
    doc.add_paragraph()
    doc.add_paragraph(f"Generated: {datetime.now().strftime('%d/%m/%Y %I:%M %p')}")
    doc.add_paragraph("This is a DRAFT document. Save it and upload to continue working.")
    
    # Save to BytesIO
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ══════════════════════════════════════════════════════════════════════════════

if "student" not in st.session_state:
    st.session_state.student = {
        "name": "", "dob": "", "age": "", "edsas": "", "program": "JP",
        "home_school": "", "key_staff": "", "clc_context": "",
        "plan_date": date.today().strftime("%d/%m/%Y"), "medical_notes": ""
    }

if "risks" not in st.session_state:
    st.session_state.risks = []

if "current_risk_idx" not in st.session_state:
    st.session_state.current_risk_idx = None

if "priority_actions" not in st.session_state:
    st.session_state.priority_actions = ""

if "review_date" not in st.session_state:
    st.session_state.review_date = ""

if "mode" not in st.session_state:
    st.session_state.mode = "student_details"  # student_details, add_risk, edit_risk, finalize

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="Safety Plan Builder (Checkpoint)", page_icon="🛡️", layout="wide")

st.markdown(f"""
<style>
.big-title {{
    background:{TEAL};color:white;padding:1.2rem;border-radius:10px;margin-bottom:1rem;
    text-align:center;font-size:1.8rem;font-weight:700;
}}
.info-box {{
    background:#d1fae5;border-left:4px solid #10b981;padding:12px;margin:12px 0;border-radius:6px;
}}
.warning-box {{
    background:#fef3c7;border-left:4px solid #f59e0b;padding:12px;margin:12px 0;border-radius:6px;
}}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">🛡️ Safety & Risk Plan Builder - Checkpoint System</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HEADER - ALWAYS SHOW SAVE/LOAD
# ══════════════════════════════════════════════════════════════════════════════

col1, col2, col3 = st.columns([2,2,2])

with col1:
    # Save checkpoint
    if st.session_state.student.get('name') and st.session_state.student.get('edsas'):
        checkpoint_json = create_checkpoint()
        student_name = st.session_state.student.get('name', 'draft').replace(' ', '_')
        checkpoint_filename = f"SafetyPlan_CHECKPOINT_{student_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        
        st.download_button(
            "💾 Save Checkpoint",
            data=checkpoint_json,
            file_name=checkpoint_filename,
            mime="application/json",
            help="Save your progress. Upload this file later to continue.",
            use_container_width=True
        )

with col2:
    # Load checkpoint
    checkpoint_upload = st.file_uploader("📂 Load Checkpoint", type=['json'], label_visibility="collapsed")
    if checkpoint_upload:
        success, message = load_checkpoint(checkpoint_upload)
        if success:
            st.success(message)
            time.sleep(1)
            st.rerun()
        else:
            st.error(message)

with col3:
    # Download current draft
    if st.session_state.risks:
        doc_buffer = create_partial_document()
        student_name = st.session_state.student.get('name', 'draft').replace(' ', '_')
        doc_filename = f"SafetyPlan_DRAFT_{student_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.docx"
        
        st.download_button(
            "📄 Download Draft Word Doc",
            data=doc_buffer,
            file_name=doc_filename,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            help="Download current progress as Word document",
            use_container_width=True
        )

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN WORKFLOW
# ══════════════════════════════════════════════════════════════════════════════

# Show current progress
student_name = st.session_state.student.get('name', 'Not entered')
risk_count = len(st.session_state.risks)

st.markdown(f"""
<div class="info-box">
<strong>Current Progress:</strong><br>
👤 Student: {student_name}<br>
⚠️ Risks: {risk_count} added<br>
💾 Mode: {st.session_state.mode.replace('_', ' ').title()}
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# MODE: STUDENT DETAILS
# ──────────────────────────────────────────────────────────────────────────────

if st.session_state.mode == "student_details":
    st.subheader("Step 1: Student Details")
    st.markdown('<div class="warning-box">⚠️ Fill out student details, then click Save & Continue. You can come back later by loading your checkpoint.</div>', unsafe_allow_html=True)
    
    s = st.session_state.student
    
    col1, col2 = st.columns(2)
    with col1:
        s['name'] = st.text_input("Full name *", value=s['name'])
        s['dob'] = st.text_input("Date of birth (DD/MM/YYYY) *", value=s['dob'])
        s['age'] = st.text_input("Age *", value=s['age'])
        s['edsas'] = st.text_input("EDSAS ID *", value=s['edsas'])
    
    with col2:
        s['program'] = st.selectbox("CLC Program *", ["JP","MP","SP","Other"], 
                                     index=["JP","MP","SP","Other"].index(s['program']) if s['program'] in ["JP","MP","SP","Other"] else 0)
        s['home_school'] = st.text_input("Home school *", value=s['home_school'])
        s['key_staff'] = st.text_input("Key CLC staff", value=s['key_staff'])
        s['plan_date'] = st.text_input("Plan date", value=s['plan_date'])
    
    s['clc_context'] = st.text_area("CLC Context", value=s['clc_context'], height=100)
    s['medical_notes'] = st.text_area("Medical & Background Notes", value=s['medical_notes'], height=100)
    
    if st.button("✅ Save & Continue to Add Risks", type="primary", use_container_width=True):
        errors = []
        if not s['name'].strip(): errors.append("Student name is required")
        if not s['dob'].strip(): errors.append("Date of birth is required")
        if not s['edsas'].strip(): errors.append("EDSAS ID is required")
        if not s['home_school'].strip(): errors.append("Home school is required")
        
        if errors:
            for e in errors:
                st.error(e)
        else:
            st.session_state.mode = "add_risk"
            st.success("✅ Student details saved! Now add risks one at a time.")
            time.sleep(1)
            st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# MODE: ADD RISK
# ──────────────────────────────────────────────────────────────────────────────

elif st.session_state.mode == "add_risk":
    st.subheader("Step 2: Add Risks (One at a Time)")
    
    # Show existing risks
    if st.session_state.risks:
        st.markdown("**Risks added so far:**")
        for i, r in enumerate(st.session_state.risks):
            col1, col2 = st.columns([4,1])
            with col1:
                st.markdown(f"{i+1}. **{r.get('issue_title', 'Untitled')}**")
            with col2:
                if st.button("Edit", key=f"edit_{i}"):
                    st.session_state.current_risk_idx = i
                    st.session_state.mode = "edit_risk"
                    st.rerun()
        st.markdown("---")
    
    # Add new risk form
    st.markdown("### Add New Risk")
    st.markdown('<div class="info-box">💡 Fill out this risk completely, then click Save Risk. You can add more risks after saving this one.</div>', unsafe_allow_html=True)
    
    with st.form("add_risk_form"):
        new_risk_title = st.text_input("Risk title *", placeholder="e.g. Absconding from CLC grounds")
        new_risk_detail = st.text_area("Behaviour description", height=100,
                                       placeholder="Describe what the student does...")
        new_risk_descriptors = st.text_area("Specific descriptors (• bullets)", height=100,
                                            placeholder="• Descriptor\n• Descriptor")
        new_risk_function = st.text_input("Function", placeholder="e.g. Avoidance - peer and adult")
        
        col1, col2 = st.columns(2)
        with col1:
            new_risk_likelihood = st.selectbox("Likelihood", [
                "A – Rare", "B – Unlikely", "C – Likely sometimes",
                "D – Likely/frequently", "E – Almost certain"
            ], index=3)
        with col2:
            new_risk_consequence = st.selectbox("Consequence", [
                "1 – Insignificant", "2 – Minor", "3 – Moderate",
                "4 – Major", "5 – Catastrophic"
            ], index=2)
        
        new_risk_proactive = st.text_area("Proactive strategies", height=150,
                                          placeholder="### Environment & supervision\n• Strategy\n• Strategy")
        new_risk_procedure = st.text_area("Reactive procedures", height=150,
                                         placeholder="### If early signs:\n• Step\n• Step")
        
        new_risk_notes = st.text_area("CLC staff notes", height=80)
        
        submit = st.form_submit_button("✅ Save This Risk", type="primary", use_container_width=True)
    
    if submit:
        if not new_risk_title.strip():
            st.error("Risk title is required")
        else:
            # Add risk to session state
            new_risk = {
                "issue_title": new_risk_title,
                "issue_detail": new_risk_detail,
                "behaviour_descriptors": new_risk_descriptors,
                "function": new_risk_function,
                "likelihood": new_risk_likelihood,
                "consequence": new_risk_consequence,
                "proactive": new_risk_proactive,
                "procedure": new_risk_procedure,
                "clc_notes": new_risk_notes
            }
            st.session_state.risks.append(new_risk)
            st.success(f"✅ Risk '{new_risk_title}' saved!")
            st.info("💾 **Important:** Download your checkpoint file now (top of page) to save this progress!")
            time.sleep(2)
            st.rerun()
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("← Back to Student Details"):
            st.session_state.mode = "student_details"
            st.rerun()
    with col2:
        if st.button("Add Another Risk", disabled=len(st.session_state.risks) == 0):
            st.rerun()
    with col3:
        if st.button("Finish & Review →", type="primary", disabled=len(st.session_state.risks) == 0):
            st.session_state.mode = "finalize"
            st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# MODE: EDIT RISK
# ──────────────────────────────────────────────────────────────────────────────

elif st.session_state.mode == "edit_risk":
    idx = st.session_state.current_risk_idx
    if idx is None or idx >= len(st.session_state.risks):
        st.session_state.mode = "add_risk"
        st.rerun()
    
    risk = st.session_state.risks[idx]
    
    st.subheader(f"Edit Risk: {risk.get('issue_title', 'Untitled')}")
    
    with st.form("edit_risk_form"):
        risk['issue_title'] = st.text_input("Risk title *", value=risk.get('issue_title', ''))
        risk['issue_detail'] = st.text_area("Behaviour description", value=risk.get('issue_detail', ''), height=100)
        risk['behaviour_descriptors'] = st.text_area("Specific descriptors", value=risk.get('behaviour_descriptors', ''), height=100)
        risk['function'] = st.text_input("Function", value=risk.get('function', ''))
        
        col1, col2 = st.columns(2)
        with col1:
            likelihood_opts = ["A – Rare", "B – Unlikely", "C – Likely sometimes", "D – Likely/frequently", "E – Almost certain"]
            lk_idx = likelihood_opts.index(risk.get('likelihood', 'D – Likely/frequently')) if risk.get('likelihood') in likelihood_opts else 3
            risk['likelihood'] = st.selectbox("Likelihood", likelihood_opts, index=lk_idx)
        with col2:
            consequence_opts = ["1 – Insignificant", "2 – Minor", "3 – Moderate", "4 – Major", "5 – Catastrophic"]
            cq_idx = consequence_opts.index(risk.get('consequence', '3 – Moderate')) if risk.get('consequence') in consequence_opts else 2
            risk['consequence'] = st.selectbox("Consequence", consequence_opts, index=cq_idx)
        
        risk['proactive'] = st.text_area("Proactive strategies", value=risk.get('proactive', ''), height=150)
        risk['procedure'] = st.text_area("Reactive procedures", value=risk.get('procedure', ''), height=150)
        risk['clc_notes'] = st.text_area("CLC staff notes", value=risk.get('clc_notes', ''), height=80)
        
        col1, col2 = st.columns(2)
        with col1:
            save = st.form_submit_button("✅ Save Changes", type="primary", use_container_width=True)
        with col2:
            delete = st.form_submit_button("🗑️ Delete Risk", use_container_width=True)
    
    if save:
        st.session_state.mode = "add_risk"
        st.success("Changes saved!")
        time.sleep(1)
        st.rerun()
    
    if delete:
        st.session_state.risks.pop(idx)
        st.session_state.mode = "add_risk"
        st.warning("Risk deleted")
        time.sleep(1)
        st.rerun()
    
    if st.button("← Cancel"):
        st.session_state.mode = "add_risk"
        st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# MODE: FINALIZE
# ──────────────────────────────────────────────────────────────────────────────

elif st.session_state.mode == "finalize":
    st.subheader("Step 3: Final Review & Priority Actions")
    
    st.markdown("### Risks Summary")
    for i, r in enumerate(st.session_state.risks, 1):
        st.markdown(f"**{i}. {r.get('issue_title', 'Untitled')}**")
    
    st.markdown("---")
    st.markdown("### Priority Actions")
    st.session_state.priority_actions = st.text_area(
        "List of actions after plan is signed",
        value=st.session_state.priority_actions,
        height=150,
        placeholder="• Schedule TAC meeting\n• Conduct fence audit\n• Staff sign-off"
    )
    
    st.markdown("### Review Date")
    st.session_state.review_date = st.text_input(
        "Next review date (DD/MM/YYYY)",
        value=st.session_state.review_date
    )
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back to Edit Risks"):
            st.session_state.mode = "add_risk"
            st.rerun()
    with col2:
        doc_buffer = create_partial_document()
        student_name = st.session_state.student.get('name', 'plan').replace(' ', '_')
        final_filename = f"SafetyPlan_FINAL_{student_name}_{datetime.now().strftime('%Y%m%d')}.docx"
        
        st.download_button(
            "📄 Download Final Plan",
            data=doc_buffer,
            file_name=final_filename,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary",
            use_container_width=True
        )

st.markdown("---")
st.markdown("""
<div style="text-align:center;color:#666;font-size:12px;">
💾 Save checkpoints regularly | 📄 Download draft documents as you go | 📂 Upload checkpoints to resume
</div>
""", unsafe_allow_html=True)
