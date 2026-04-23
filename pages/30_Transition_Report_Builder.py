import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import io

# Page config
st.set_page_config(page_title="Transition Report Builder", layout="wide", page_icon="📄")

# Main app
st.title("📄 Transition Report Builder")
st.markdown("Generate comprehensive transition reports")

# Sidebar for student selection
with st.sidebar:
    st.header("Report Configuration")
    
    # Manual student entry
    student_first_name = st.text_input("Student First Name *")
    student_last_name = st.text_input("Student Last Name *")
    
    if not student_first_name or not student_last_name:
        st.warning("Enter student name to continue")
        st.stop()
    
    selected_student_name = f"{student_first_name} {student_last_name}"
    selected_student = {
        'first_name': student_first_name,
        'last_name': student_last_name,
        'id': 'manual'
    }
    
    st.markdown("---")
    
    report_date = st.date_input("Report Date", value=date.today())
    placement_start = st.date_input("Placement Start Date")
    placement_end = st.date_input("Placement End Date", value=date.today())
    
    st.markdown("---")
    
    lc_teacher = st.text_input("LC Teacher Name", value="")
    enrolled_school = st.text_input("Enrolled School", value="")

# Main content tabs
tab1, tab2, tab3 = st.tabs(["📝 Report Sections", "👁️ Preview", "💾 Generate"])

# TAB 1: Report Sections
with tab1:
    st.header(f"Transition Report: {selected_student_name}")
    
    # LITERACY PROGRESS
    st.subheader("📖 Literacy Progress")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Word Aware (Vocabulary)**")
        vocab_pre_assessment = st.text_input("Pre-Assessment Type", key="vocab_pre_type")
        vocab_pre_score = st.text_input("Pre Score", key="vocab_pre", placeholder="/5")
        vocab_post_score = st.text_input("Post Score", key="vocab_post", placeholder="/5")
        vocab_summary = st.text_area("Summary", key="vocab_summary", height=80)
    
    with col2:
        st.markdown("**Sounds Write Progress**")
        st.caption("Leave blank if not assessed")
    
    # Sounds Write table
    st.markdown("**Sounds Write Assessments**")
    sounds_write_data = {
        "Skill": [
            "Blending (building words)",
            "Segmenting (identifying sounds)",
            "Phoneme Manipulation",
            "Alphabet Code Knowledge",
            "Non-Word Reading"
        ],
        "Max Score": [14, 69, 10, 50, 30],
        "Pre": ["", "", "", "", ""],
        "Post": ["", "", "", "", ""],
        "Summary": ["", "", "", "", ""]
    }
    
    sounds_write_df = pd.DataFrame(sounds_write_data)
    edited_sw = st.data_editor(
        sounds_write_df,
        hide_index=True,
        use_container_width=True,
        key="sounds_write_data"
    )
    
    st.markdown("---")
    
    # NUMERACY PROGRESS
    st.subheader("🔢 Numeracy Progress")
    numeracy_assessment = st.text_area(
        "Numeracy Assessment Details",
        placeholder="Describe numeracy assessments, progress, and key achievements...",
        height=150,
        key="numeracy"
    )
    
    st.markdown("---")
    
    # HIGH IMPACT TEACHING STRATEGIES
    st.subheader("🎯 Pedagogical Strategies (HITS)")
    
    hits_options = [
        "Goal Setting",
        "Structuring Lessons",
        "Explicit Teaching",
        "Worked Examples",
        "Collaborative Learning",
        "Multiple Exposures",
        "Questioning",
        "Feedback",
        "Metacognitive Strategies",
        "Differentiated Teaching"
    ]
    
    selected_hits = st.multiselect(
        "Select strategies that promoted positive engagement",
        options=hits_options,
        key="hits_strategies"
    )
    
    hits_comments = st.text_area(
        "Comments on pedagogical strategies",
        placeholder="Describe how these strategies supported the student's learning...",
        height=100,
        key="hits_comments"
    )
    
    st.markdown("---")
    
    # RESTORATIVE PRACTICE
    st.subheader("🤝 Restorative Practice & Relational Safety")
    
    restorative_strategies = st.multiselect(
        "Restorative strategies used",
        options=[
            "Comic Strip Conversations",
            "Circles (Nurture/Restorative/Community)",
            "Restorative Meetings",
            "Relational Mapping",
            "Restorative Conversations",
            "Affective Questioning/Statements"
        ],
        key="restorative"
    )
    
    restorative_comments = st.text_area(
        "Comments on restorative practice",
        placeholder="Describe relational safety strategies and their effectiveness...",
        height=100,
        key="restorative_comments"
    )
    
    st.markdown("---")
    
    # REGULATION PROFILE (Pull from WOT if available)
    st.subheader("🎯 Regulation Profile (Window of Tolerance)")
    
    st.info("Enter Window of Tolerance data manually")
    
    regulation_summary = st.text_area(
        "Regulation Profile Summary",
        placeholder="Describe typical arousal patterns, triggers, and effective co-regulation strategies...",
        height=120,
        key="regulation"
    )
    
    st.markdown("---")
    
    # BEHAVIOUR PROGRESS (SMARTAR Goals)
    st.subheader("📊 Behaviour Progress: SMARTAR Goals")
    
    st.info("Enter SMARTAR goals manually")
    num_goals = st.number_input("Number of goals to include", min_value=1, max_value=3, value=2)
    
    for idx in range(1, num_goals + 1):
        with st.expander(f"Goal {idx}", expanded=True):
            st.text_input(f"Exclusion Goal {idx}", key=f"excl_{idx}")
            st.text_input(f"SMARTAR Goal {idx}", key=f"smartar_{idx}")
            
            st.markdown("**Goal Attainment Scale**")
            st.text_input(f"Exceeding Expectation {idx}", key=f"gas_exceed_{idx}")
            st.text_input(f"Above Expectation {idx}", key=f"gas_above_{idx}")
            st.text_input(f"Expected Goal {idx}", key=f"gas_expected_{idx}")
            st.text_input(f"Below Expectation {idx}", key=f"gas_below_{idx}")
            st.text_input(f"Well Below Expectation {idx}", key=f"gas_wellbelow_{idx}")
            
            st.selectbox(
                f"Current achievement level",
                options=["Exceeding Expectation", "Above Expectation", "Expected Goal", "Below Expectation", "Well Below"],
                index=2,
                key=f"gas_current_{idx}"
            )
    
    st.markdown("---")
    
    # ATTENDANCE & SUMMARY
    st.subheader("📅 Attendance & Progress Summary")
    
    col1, col2 = st.columns(2)
    with col1:
        days_attended = st.number_input("Days Attended", min_value=0, value=0, key="days_attended")
        total_days = st.number_input("Total Days", min_value=1, value=1, key="total_days")
    
    with col2:
        attendance_pct = (days_attended / total_days * 100) if total_days > 0 else 0
        st.metric("Attendance Rate", f"{attendance_pct:.1f}%")
    
    progress_summary = st.text_area(
        "Overall Progress Summary",
        placeholder="Summarize key achievements, challenges, and demonstrated growth...",
        height=150,
        key="progress_summary"
    )
    
    transition_recommendations = st.text_area(
        "Transition Recommendations",
        placeholder="Specific strategies, accommodations, or supports recommended for successful transition...",
        height=150,
        key="recommendations"
    )

# TAB 2: Preview
with tab2:
    st.header("Report Preview")
    st.info("Preview functionality - shows key sections summary")
    
    if st.button("Show Preview"):
        st.markdown(f"### Transition Report: {selected_student_name}")
        st.markdown(f"**Report Date:** {report_date}")
        st.markdown(f"**Placement Period:** {placement_start} to {placement_end}")
        st.markdown(f"**LC Teacher:** {lc_teacher}")
        st.markdown(f"**Enrolled School:** {enrolled_school}")
        
        st.markdown("---")
        st.markdown("**Literacy Progress:**")
        st.write(f"Vocabulary: Pre {st.session_state.get('vocab_pre', 'N/A')}, Post {st.session_state.get('vocab_post', 'N/A')}")
        
        st.markdown("**HITS Strategies:**")
        st.write(", ".join(selected_hits) if selected_hits else "None selected")
        
        st.markdown("**Attendance:**")
        st.write(f"{days_attended} of {total_days} days ({attendance_pct:.1f}%)")

# TAB 3: Generate Document
with tab3:
    st.header("Generate Transition Report")
    
    st.markdown("""
    Click below to generate the complete Word document with all entered data.
    The document will use the professional template format.
    """)
    
    if st.button("📄 Generate Report Data", type="primary", use_container_width=True):
        if not lc_teacher or not enrolled_school:
            st.error("Please enter LC Teacher name and Enrolled School in the sidebar")
        else:
            with st.spinner("Preparing report data..."):
                
                # Collect all report data
                report_data = {
                    "student": selected_student,
                    "report_date": report_date,
                    "placement_start": placement_start,
                    "placement_end": placement_end,
                    "lc_teacher": lc_teacher,
                    "enrolled_school": enrolled_school,
                    "literacy": {
                        "vocab_pre": st.session_state.get('vocab_pre', ''),
                        "vocab_post": st.session_state.get('vocab_post', ''),
                        "vocab_summary": st.session_state.get('vocab_summary', ''),
                        "sounds_write": edited_sw.to_dict()
                    },
                    "numeracy": st.session_state.get('numeracy', ''),
                    "hits": {
                        "strategies": selected_hits,
                        "comments": st.session_state.get('hits_comments', '')
                    },
                    "restorative": {
                        "strategies": restorative_strategies,
                        "comments": st.session_state.get('restorative_comments', '')
                    },
                    "regulation": st.session_state.get('regulation', ''),
                    "attendance": {
                        "attended": days_attended,
                        "total": total_days
                    },
                    "summary": st.session_state.get('progress_summary', ''),
                    "recommendations": st.session_state.get('recommendations', '')
                }
                
                st.success("✅ Report data prepared!")
                st.json(report_data)
                
                st.info("""
                📝 **Next Steps:**
                
                The report data is ready. To generate the Word document:
                
                1. Add `python-docx` to your requirements.txt
                2. Push to GitHub and wait for Render to redeploy
                3. Return here to generate the formatted Word document
                
                For now, you can copy the data above for manual report creation.
                """)

st.markdown("---")
st.caption("Transition Report Builder | Cowandilla Learning Centre LBU")
