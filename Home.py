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

st.markdown(f"### 👋 Welcome, {staff_name} — {today}")
st.markdown("Use the links below to open each app, or visit the [staff portal home](https://16cefb77.clc-portal.pages.dev/).")

st.page_link("pages/1_Daily_Bulletin.py", label="📰 Daily Bulletin", use_container_width=True)
st.page_link("pages/2_Timetable.py", label="📅 Timetable", use_container_width=True)
st.page_link("pages/3_Team_Meetings.py", label="👥 Team Meetings", use_container_width=True)
st.page_link("pages/5_Behaviour_Support.py", label="📊 Behaviour Support", use_container_width=True)
st.page_link("pages/7_Sensory_Overview.py", label="🧠 Sensory Overview", use_container_width=True)
st.page_link("pages/8_Sensory_Profile.py", label="📋 Sensory Profile", use_container_width=True)
st.page_link("pages/10_Document_Library.py", label="📁 Document Library", use_container_width=True)
st.page_link("pages/11_Digital_Staff_Meeting.py", label="🗓 Digital Staff Meeting", use_container_width=True)
st.page_link("pages/12_Calendar.py", label="📆 Calendar", use_container_width=True)
st.page_link("pages/13_Footy_Tipping.py", label="🏈 Footy Tipping", use_container_width=True)
st.page_link("pages/14_Committees.py", label="🏛 Committees", use_container_width=True)
