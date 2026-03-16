from theme import apply_clc_theme
from auth import require_auth, logout_button, get_staff_name
import streamlit as st
from supabase import create_client
from datetime import date, datetime
import pandas as pd
import os

st.set_page_config(page_title="Engagement Tracker", page_icon="🎯", layout="wide", initial_sidebar_state="collapsed")
apply_clc_theme()
require_auth("Engagement Tracker", "🎯")
logout_button("sidebar")

PORTAL_URL = "https://16cefb77.clc-portal.pages.dev/"
st.sidebar.markdown(
    f'<a href="{PORTAL_URL}" target="_self" style="display:block;text-align:center;background:#1A7A7A;color:white;font-weight:600;font-size:0.85rem;padding:0.5rem;border-radius:8px;text-decoration:none;margin-bottom:0.5rem;">🏠 Back to Staff Portal</a>',
    unsafe_allow_html=True
)

TEAL = "#1A7A7A"
AMBER = "#C8760A"

@st.cache_resource(ttl=60)
def get_supabase():
    try:
        url = st.secrets.get("supabase", {}).get("url") or st.secrets.get("BEHAVIOUR_SUPABASE_URL", "")
        key = st.secrets.get("supabase", {}).get("key") or st.secrets.get("BEHAVIOUR_SUPABASE_KEY", "")
    except Exception:
        url = os.environ.get("BEHAVIOUR_SUPABASE_URL", "")
        key = os.environ.get("BEHAVIOUR_SUPABASE_KEY", "")
    return create_client(url, key)

supabase = get_supabase()

def load_students():
    try:
        res = supabase.table("engagement_students").select("*").order("name").execute()
        return res.data or []
    except Exception as e:
        st.error(f"Could not load students: {e}")
        return []

def load_entries(student_id=None):
    try:
        q = supabase.table("engagement_entries").select("*").order("created_at", desc=True)
        if student_id:
            q = q.eq("student_id", student_id)
        res = q.execute()
        return res.data or []
    except Exception as e:
        st.error(f"Could not load entries: {e}")
        return []

def save_entry(entry):
    try:
        supabase.table("engagement_entries").insert(entry).execute()
        return True
    except Exception as e:
        st.error(f"Could not save entry: {e}")
        return False

def add_student(name, program, year_level):
    try:
        supabase.table("engagement_students").insert({
            "name": name,
            "program": program,
            "year_level": year_level,
        }).execute()
        return True
    except Exception as e:
        st.error(f"Could not add student: {e}")
        return False

# ── Header ────────────────────────────────────────────────────
st.markdown(f"""
<div style="background:linear-gradient(135deg,{TEAL},{AMBER});padding:1.5rem 2rem;border-radius:12px;margin-bottom:1.5rem;color:white;">
  <div style="font-size:1.5rem;font-weight:700;">🎯 Engagement Tracker</div>
  <div style="font-size:0.85rem;opacity:0.85;">Log and monitor student engagement data · Cowandilla Learning Centre</div>
</div>
""", unsafe_allow_html=True)

tab_log, tab_view, tab_students = st.tabs(["📝 Log Engagement", "📊 View Data", "👤 Students"])

# ══════════════════════════════════════════════════════════════
# TAB: LOG ENGAGEMENT
# ══════════════════════════════════════════════════════════════
with tab_log:
    students = load_students()
    if not students:
        st.warning("No students found. Add students in the Students tab first.")
    else:
        student_options = {s["id"]: f"{s['name']} ({s.get('program','?')})" for s in students}
        
        col1, col2 = st.columns(2)
        with col1:
            selected_id = st.selectbox("Student", options=list(student_options.keys()), 
                                        format_func=lambda x: student_options[x], key="log_student")
            entry_date = st.date_input("Date", value=date.today())
            session_type = st.selectbox("Session Type", ["", "JP", "PY", "SY", "NIT", "Individual", "Group", "Community"])
        with col2:
            engagement_level = st.select_slider("Engagement Level", 
                options=["1 - Very Low", "2 - Low", "3 - Moderate", "4 - Good", "5 - High"],
                value="3 - Moderate")
            support_type = st.selectbox("Support Type", ["", "Independent", "Verbal Prompt", "Gestural Prompt", 
                                                           "Physical Prompt", "Full Support", "Modified Task"])
            duration_mins = st.number_input("Duration (minutes)", min_value=0, max_value=360, value=30, step=5)

        activity = st.text_input("Activity / Task", placeholder="e.g. Literacy rotation, maths game")
        notes = st.text_area("Notes", placeholder="Any relevant observations...", height=100)
        staff_name = get_staff_name()

        if st.button("💾 Save Entry", type="primary", use_container_width=True):
            if not selected_id:
                st.warning("Please select a student.")
            else:
                entry = {
                    "student_id": selected_id,
                    "entry_date": str(entry_date),
                    "session_type": session_type,
                    "engagement_level": int(engagement_level[0]),
                    "support_type": support_type,
                    "duration_mins": duration_mins,
                    "activity": activity,
                    "notes": notes,
                    "recorded_by": staff_name,
                    "created_at": datetime.utcnow().isoformat(),
                }
                if save_entry(entry):
                    st.success("✅ Engagement entry saved!")
                    st.rerun()

# ══════════════════════════════════════════════════════════════
# TAB: VIEW DATA
# ══════════════════════════════════════════════════════════════
with tab_view:
    students = load_students()
    if not students:
        st.warning("No students found.")
    else:
        student_options = {"all": "All Students"} | {s["id"]: s["name"] for s in students}
        filter_student = st.selectbox("Filter by student", options=list(student_options.keys()),
                                       format_func=lambda x: student_options[x])
        
        entries = load_entries(student_id=None if filter_student == "all" else filter_student)
        
        if not entries:
            st.info("No engagement entries found.")
        else:
            # Build student name lookup
            name_map = {s["id"]: s["name"] for s in students}
            
            df = pd.DataFrame(entries)
            df["student_name"] = df["student_id"].map(name_map)
            df["entry_date"] = pd.to_datetime(df["entry_date"])
            
            # Summary metrics
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Total Entries", len(df))
            with m2:
                avg_eng = df["engagement_level"].mean()
                st.metric("Avg Engagement", f"{avg_eng:.1f}/5")
            with m3:
                total_mins = df["duration_mins"].sum()
                st.metric("Total Minutes", f"{total_mins:,}")
            with m4:
                unique_students = df["student_name"].nunique()
                st.metric("Students", unique_students)
            
            st.markdown("---")
            
            # Engagement over time chart
            if len(df) > 1:
                import plotly.express as px
                fig = px.line(
                    df.sort_values("entry_date"),
                    x="entry_date", y="engagement_level",
                    color="student_name",
                    title="Engagement Over Time",
                    labels={"engagement_level": "Engagement (1-5)", "entry_date": "Date"},
                    color_discrete_sequence=[TEAL, AMBER, "#4a7fb5", "#7a5bb5", "#6a7f8a"]
                )
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
            
            # Data table
            st.markdown("**Recent Entries:**")
            display_df = df[["entry_date", "student_name", "session_type", "engagement_level", 
                              "support_type", "duration_mins", "activity", "recorded_by"]].copy()
            display_df["entry_date"] = display_df["entry_date"].dt.strftime("%-d %b %Y")
            display_df.columns = ["Date", "Student", "Session", "Engagement", "Support", "Mins", "Activity", "Staff"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Download
            csv = display_df.to_csv(index=False)
            st.download_button("📥 Download CSV", data=csv, 
                               file_name=f"engagement_data_{date.today()}.csv",
                               mime="text/csv")

# ══════════════════════════════════════════════════════════════
# TAB: STUDENTS
# ══════════════════════════════════════════════════════════════
with tab_students:
    students = load_students()
    
    if students:
        st.markdown(f"**{len(students)} students registered:**")
        df_s = pd.DataFrame(students)[["name", "program", "year_level"]]
        df_s.columns = ["Name", "Program", "Year Level"]
        st.dataframe(df_s, use_container_width=True, hide_index=True)
    else:
        st.info("No students yet.")
    
    st.markdown("---")
    st.markdown("**Add a student:**")
    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        new_name = st.text_input("Name", key="new_student_name")
    with ac2:
        new_program = st.selectbox("Program", ["", "JP", "PY", "SY"], key="new_student_program")
    with ac3:
        new_year = st.text_input("Year Level", key="new_student_year")
    
    if st.button("➕ Add Student", type="primary"):
        if new_name.strip():
            if add_student(new_name.strip(), new_program, new_year.strip()):
                st.success(f"✅ {new_name} added!")
                st.rerun()
        else:
            st.warning("Please enter a name.")
