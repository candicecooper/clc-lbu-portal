# ==============================================================================
# 18_Scatter_Plot_Tracker.py - CLC-LBU Portal
# Simple Paper-Style Scatter Plot Tracker
# ==============================================================================
import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
import json

from auth import require_auth, logout_button, get_staff_name
# require_auth(app_title="CLC LBU Staff Portal", app_icon="🏫")
# logout_button()

TEAL = "#1A7A6E"
AMBER = "#C8760A"

st.set_page_config(page_title="Scatter Plot Tracker", layout="wide")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background:#f5f8fa; }
.header {
    background:linear-gradient(135deg,#1A7A6E 0%,#1A7A6EBB 100%);
    color:white; padding:1rem 1.5rem; border-radius:10px; margin-bottom:1.5rem;
}
.header h1 { margin:0; font-size:1.8rem; }
.header p { margin:.3rem 0 0; opacity:.9; font-size:.9rem; }
.grid-container {
    background:white; border:2px solid #cbd5e1; border-radius:10px;
    padding:1rem; margin-top:1rem;
}
.week-grid {
    width:100%; border-collapse:collapse; font-size:.85rem;
    margin-top:1rem;
}
.week-grid th {
    background:#1A7A6E; color:white; padding:.6rem .4rem;
    text-align:center; font-weight:600; border:1px solid #0f5f56;
}
.week-grid td {
    border:1px solid #cbd5e1; padding:.5rem .3rem;
    text-align:center; min-width:45px; cursor:pointer;
}
.week-grid td:hover { background:#e0f2fe; }
.week-grid .time-cell { 
    background:#f1f5f9; font-weight:600; text-align:left;
    padding-left:.6rem; white-space:nowrap;
}
.week-grid .activity-cell {
    background:#f8fafc; text-align:left; padding-left:.6rem;
    font-style:italic; font-size:.8rem; color:#64748b;
}
.week-grid .total-cell {
    background:#fef3c7; font-weight:700; color:#92400e;
}
.week-grid .total-row {
    background:#fef3c7; font-weight:700; color:#92400e;
    font-size:.9rem;
}
.tally { color:#dc2626; font-weight:700; font-size:1.1rem; }
.info-box {
    background:#f0f9ff; border-left:4px solid #0284c7;
    padding:.7rem 1rem; border-radius:6px; margin:.5rem 0;
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# SUPABASE
# ==============================================================================
def get_sb():
    try:
        from supabase import create_client
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except:
        return None

# ==============================================================================
# SESSION STATE
# ==============================================================================
def init():
    if 'page' not in st.session_state:
        st.session_state.page = 'setup'
    if 'student_name' not in st.session_state:
        st.session_state.student_name = ''
    if 'week_start' not in st.session_state:
        st.session_state.week_start = date.today() - timedelta(days=date.today().weekday())
    if 'behaviours' not in st.session_state:
        st.session_state.behaviours = []
    if 'schedule' not in st.session_state:
        st.session_state.schedule = []
    if 'grid_data' not in st.session_state:
        st.session_state.grid_data = {}

init()

# ==============================================================================
# HEADER
# ==============================================================================
st.markdown("""
<div class='header'>
<h1>📊 Scatter Plot Tracker</h1>
<p>Simple paper-style weekly behaviour recording</p>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# PAGE NAVIGATION
# ==============================================================================
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("📋 Setup Week", use_container_width=True, type="primary" if st.session_state.page == 'setup' else "secondary"):
        st.session_state.page = 'setup'
        st.rerun()
with col2:
    if st.button("✏️ Record Behaviours", use_container_width=True, type="primary" if st.session_state.page == 'record' else "secondary"):
        st.session_state.page = 'record'
        st.rerun()

st.markdown("---")

# ==============================================================================
# PAGE 1: SETUP
# ==============================================================================
if st.session_state.page == 'setup':
    st.markdown("## 📋 Weekly Setup")
    st.caption("Set up your tracking sheet for the week")
    
    # Student selection
    st.markdown("### 1. Student")
    
    @st.cache_data(ttl=120)
    def load_students():
        sb = get_sb()
        if not sb: return []
        try:
            res = sb.table("scatter_students").select("*").order("student_name").execute()
            return res.data or []
        except:
            return []
    
    students = load_students()
    
    if not students:
        st.warning("⚠️ No students found. Add a student first.")
        new_name = st.text_input("Student Name")
        new_prog = st.selectbox("Program", ["JP", "PY", "SY"])
        if st.button("Add Student", type="primary"):
            sb = get_sb()
            if sb and new_name:
                try:
                    sb.table("scatter_students").insert({
                        "student_name": new_name.strip(),
                        "program_type": new_prog
                    }).execute()
                    st.success(f"✅ Added {new_name}")
                    load_students.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        student_names = [s['student_name'] for s in students]
        selected = st.selectbox(
            "Select Student",
            options=student_names,
            index=student_names.index(st.session_state.student_name) if st.session_state.student_name in student_names else 0
        )
        st.session_state.student_name = selected
    
    st.markdown("---")
    
    # Week selection
    st.markdown("### 2. Week")
    col1, col2 = st.columns(2)
    with col1:
        week_start = st.date_input(
            "Monday (start of week)",
            value=st.session_state.week_start,
            help="Select the Monday of the tracking week"
        )
        st.session_state.week_start = week_start
    with col2:
        week_end = week_start + timedelta(days=4)
        st.info(f"📅 Week: {week_start.strftime('%-d %b')} - {week_end.strftime('%-d %b %Y')}")
    
    st.markdown("---")
    
    # Target behaviours
    st.markdown("### 3. Target Behaviours")
    st.caption("Enter 1-3 behaviours to track this week (e.g., 'Hitting', 'Task refusal', 'Yelling')")
    
    beh1 = st.text_input("Behaviour 1", value=st.session_state.behaviours[0] if len(st.session_state.behaviours) > 0 else "", key="beh1")
    beh2 = st.text_input("Behaviour 2 (optional)", value=st.session_state.behaviours[1] if len(st.session_state.behaviours) > 1 else "", key="beh2")
    beh3 = st.text_input("Behaviour 3 (optional)", value=st.session_state.behaviours[2] if len(st.session_state.behaviours) > 2 else "", key="beh3")
    
    behaviours = [b.strip() for b in [beh1, beh2, beh3] if b.strip()]
    st.session_state.behaviours = behaviours
    
    if behaviours:
        st.success(f"✅ Tracking: {', '.join(behaviours)}")
    
    st.markdown("---")
    
    # Schedule
    st.markdown("### 4. Daily Schedule")
    st.caption("Enter your time slots and activities (e.g., '9:00 - Maths', '10:30 - Recess')")
    
    # Default schedule
    if not st.session_state.schedule:
        st.session_state.schedule = [
            {"time": "9:00", "activity": "Morning routine"},
            {"time": "9:30", "activity": "Lesson 1"},
            {"time": "10:30", "activity": "Recess"},
            {"time": "11:00", "activity": "Lesson 2"},
            {"time": "12:30", "activity": "Lunch"},
            {"time": "13:00", "activity": "Lesson 3"},
            {"time": "14:00", "activity": "Pack up"},
        ]
    
    schedule_data = pd.DataFrame(st.session_state.schedule)
    
    edited_schedule = st.data_editor(
        schedule_data,
        column_config={
            "time": st.column_config.TextColumn("Time", width="small"),
            "activity": st.column_config.TextColumn("Activity", width="medium")
        },
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True
    )
    
    st.session_state.schedule = edited_schedule.to_dict('records')
    
    st.markdown("---")
    
    # Save and continue
    if st.button("✅ Setup Complete - Start Recording", type="primary", use_container_width=True):
        if not st.session_state.student_name:
            st.error("❌ Please select a student")
        elif not behaviours:
            st.error("❌ Please enter at least one behaviour")
        elif not st.session_state.schedule:
            st.error("❌ Please add your daily schedule")
        else:
            st.session_state.page = 'record'
            st.rerun()

# ==============================================================================
# PAGE 2: RECORDING GRID
# ==============================================================================
elif st.session_state.page == 'record':
    
    if not st.session_state.student_name or not st.session_state.behaviours:
        st.warning("⚠️ Please complete setup first")
        if st.button("Go to Setup"):
            st.session_state.page = 'setup'
            st.rerun()
        st.stop()
    
    st.markdown(f"## ✏️ Recording: {st.session_state.student_name}")
    
    week_start = st.session_state.week_start
    week_end = week_start + timedelta(days=4)
    
    st.markdown(f"<div class='info-box'><b>Week:</b> {week_start.strftime('%-d %b')} - {week_end.strftime('%-d %b %Y')} | <b>Behaviours:</b> {', '.join(st.session_state.behaviours)}</div>", unsafe_allow_html=True)
    
    # Days of week
    days = []
    for i in range(5):
        day_date = week_start + timedelta(days=i)
        days.append({
            "name": day_date.strftime("%A"),
            "short": day_date.strftime("%a"),
            "date": day_date.strftime("%-d/%-m"),
            "date_obj": day_date
        })
    
    behaviours = st.session_state.behaviours
    schedule = st.session_state.schedule
    
    # Initialize grid data if needed
    if not st.session_state.grid_data:
        st.session_state.grid_data = {}
    
    st.markdown("### 📊 Weekly Grid")
    st.caption("Click any cell to add a tally mark ( / ). Click repeatedly to add more.")
    
    # Build grid as DataFrame for display
    grid_rows = []
    
    for slot in schedule:
        time = slot['time']
        activity = slot.get('activity', '')
        
        row = {"Time": time, "Activity": activity}
        
        for day in days:
            for beh_idx, beh in enumerate(behaviours):
                cell_key = f"{day['date_obj']}_{time}_{beh_idx}"
                current_value = st.session_state.grid_data.get(cell_key, 0)
                
                # Display tally marks
                if current_value == 0:
                    display = ""
                elif current_value <= 4:
                    display = "/" * current_value
                else:
                    display = str(current_value)
                
                col_name = f"{day['short']}_{beh[:8]}"
                row[col_name] = display
        
        # Row total
        row_total = sum(st.session_state.grid_data.get(f"{d['date_obj']}_{time}_{i}", 0) 
                       for d in days for i in range(len(behaviours)))
        row["Total"] = str(row_total) if row_total > 0 else ""
        
        grid_rows.append(row)
    
    # Add totals row
    totals_row = {"Time": "TOTAL", "Activity": ""}
    week_total = 0
    
    for day in days:
        for beh_idx, beh in enumerate(behaviours):
            day_beh_total = sum(st.session_state.grid_data.get(f"{day['date_obj']}_{s['time']}_{beh_idx}", 0) 
                               for s in schedule)
            col_name = f"{day['short']}_{beh[:8]}"
            totals_row[col_name] = str(day_beh_total) if day_beh_total > 0 else ""
            week_total += day_beh_total
    
    totals_row["Total"] = str(week_total)
    grid_rows.append(totals_row)
    
    # Display grid
    grid_df = pd.DataFrame(grid_rows)
    st.dataframe(grid_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Quick recording interface
    st.markdown("### ✏️ Quick Record")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        record_day = st.selectbox("Day", [d['name'] for d in days])
        day_obj = [d for d in days if d['name'] == record_day][0]['date_obj']
    
    with col2:
        record_time = st.selectbox("Time", [s['time'] for s in schedule])
    
    with col3:
        record_beh = st.selectbox("Behaviour", behaviours)
        beh_idx = behaviours.index(record_beh)
    
    cell_key = f"{day_obj}_{record_time}_{beh_idx}"
    current = st.session_state.grid_data.get(cell_key, 0)
    
    st.info(f"Current value: **{current}** {'/' * current if current <= 4 else ''}")
    
    col_add, col_minus, col_set = st.columns(3)
    
    with col_add:
        if st.button("➕ Add Tally ( / )", use_container_width=True, type="primary"):
            st.session_state.grid_data[cell_key] = current + 1
            st.rerun()
    
    with col_minus:
        if st.button("➖ Remove Tally", use_container_width=True):
            if current > 0:
                st.session_state.grid_data[cell_key] = current - 1
                st.rerun()
    
    with col_set:
        set_value = st.number_input("Or set to:", min_value=0, max_value=20, value=current, key="set_val", label_visibility="collapsed")
        if st.button("✏️ Set", use_container_width=True):
            st.session_state.grid_data[cell_key] = set_value
            st.rerun()
    
    st.markdown("---")
    
    # Save/Load
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Save Week", use_container_width=True):
            sb = get_sb()
            if sb:
                try:
                    # Save as JSON blob
                    sb.table("scatter_weekly_data").upsert({
                        "student_name": st.session_state.student_name,
                        "week_start": str(week_start),
                        "behaviours": json.dumps(behaviours),
                        "schedule": json.dumps(schedule),
                        "grid_data": json.dumps(st.session_state.grid_data),
                        "created_by": get_staff_name() if hasattr(get_staff_name, '__call__') else "Staff"
                    }).execute()
                    st.success("✅ Week saved!")
                except Exception as e:
                    st.error(f"Save failed: {e}")
    
    with col2:
        if st.button("📥 Load Week", use_container_width=True):
            sb = get_sb()
            if sb:
                try:
                    res = sb.table("scatter_weekly_data").select("*").eq("student_name", st.session_state.student_name).eq("week_start", str(week_start)).execute()
                    if res.data:
                        data = res.data[0]
                        st.session_state.grid_data = json.loads(data.get('grid_data', '{}'))
                        st.success("✅ Week loaded!")
                        st.rerun()
                    else:
                        st.info("No saved data for this week")
                except Exception as e:
                    st.error(f"Load failed: {e}")
    
    with col3:
        if st.button("🗑️ Clear All", use_container_width=True):
            if st.checkbox("Confirm clear all data"):
                st.session_state.grid_data = {}
                st.rerun()

st.markdown("---")
st.caption("🏫 CLC-LBU · Simple Scatter Plot Tracker")
