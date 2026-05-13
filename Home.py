from theme import apply_clc_theme
import streamlit as st
from auth import require_auth, logout_button, get_staff_name
from datetime import date

st.set_page_config(page_title="CLC LBU Staff Portal", page_icon="🏫", layout="wide", initial_sidebar_state="collapsed")
apply_clc_theme()
require_auth("CLC LBU Staff Portal", "🏫")
logout_button("sidebar")

staff_name = get_staff_name()
today = date.today().strftime("%A %-d %B %Y")
BASE = "https://clc-lbu-portal.onrender.com"

st.markdown(f"### 👋 Welcome, {staff_name} — {today}")
st.markdown(f"""
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-top:1rem;">
  <a href="{BASE}/Daily_Bulletin" style="display:block;background:#1A7A7A;color:white;padding:1rem;border-radius:10px;text-decoration:none;font-weight:600;">📰 Daily Bulletin</a>
  <a href="{BASE}/Timetable" style="display:block;background:#1A7A7A;color:white;padding:1rem;border-radius:10px;text-decoration:none;font-weight:600;">📅 Timetable</a>
  <a href="{BASE}/Team_Meetings" style="display:block;background:#1A7A7A;color:white;padding:1rem;border-radius:10px;text-decoration:none;font-weight:600;">👥 Team Meetings</a>
  <a href="{BASE}/Digital_Staff_Meeting" style="display:block;background:#1A7A7A;color:white;padding:1rem;border-radius:10px;text-decoration:none;font-weight:600;">🗓 Digital Staff Meeting</a>
  <a href="{BASE}/Behaviour_Support" style="display:block;background:#1A7A7A;color:white;padding:1rem;border-radius:10px;text-decoration:none;font-weight:600;">📊 Behaviour Support</a>
  <a href="{BASE}/Sensory_Overview" style="display:block;background:#1A7A7A;color:white;padding:1rem;border-radius:10px;text-decoration:none;font-weight:600;">🧠 Sensory Overview</a>
  <a href="{BASE}/Sensory_Profile" style="display:block;background:#1A7A7A;color:white;padding:1rem;border-radius:10px;text-decoration:none;font-weight:600;">📋 Sensory Profile</a>
  <a href="{BASE}/Engagement_Tracker" style="display:block;background:#1A7A7A;color:white;padding:1rem;border-radius:10px;text-decoration:none;font-weight:600;">🎯 Engagement Tracker</a>
  <a href="{BASE}/Document_Library" style="display:block;background:#1A7A7A;color:white;padding:1rem;border-radius:10px;text-decoration:none;font-weight:600;">📁 Document Library</a>
  <a href="{BASE}/Calendar" style="display:block;background:#1A7A7A;color:white;padding:1rem;border-radius:10px;text-decoration:none;font-weight:600;">📆 Calendar</a>
  <a href="{BASE}/Scatter_Plot_Tracker" style="display:block;background:#1A7A7A;color:white;padding:1rem;border-radius:10px;text-decoration:none;font-weight:600;">📊 Scatter Plot Tracker</a>
  <a href="{BASE}/Student_Schedule_Analysis" style="display:block;background:#1A7A7A;color:white;padding:1rem;border-radius:10px;text-decoration:none;font-weight:600;">🗂️ Schedule Analysis</a>
  <a href="{BASE}/Allocation_Meetings_Tool" style="display:block;background:#1A7A7A;color:white;padding:1rem;border-radius:10px;text-decoration:none;font-weight:600;">📋 Allocation Meetings</a>
  <a href="{BASE}/Footy_Tipping" style="display:block;background:#C8760A;color:white;padding:1rem;border-radius:10px;text-decoration:none;font-weight:600;">🏈 Footy Tipping</a>
  <a href="{BASE}/Committees" style="display:block;background:#C8760A;color:white;padding:1rem;border-radius:10px;text-decoration:none;font-weight:600;">🏛 Committees</a>
  <a href="{BASE}/Leadership" style="display:block;background:#0f5f5f;color:white;padding:1rem;border-radius:10px;text-decoration:none;font-weight:600;">👔 Leadership</a>
</div>
""", unsafe_allow_html=True)
