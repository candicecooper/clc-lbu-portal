from theme import apply_clc_theme
import streamlit as st
from auth import require_auth, logout_button, get_staff_name

st.set_page_config(
    page_title="CLC LBU Staff Portal",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Use st.navigation to hide sidebar page list ────────────────────────────
pg = st.navigation(
    [
        st.Page("pages/1_Daily_Bulletin.py",       title="Daily Bulletin",        icon="📰"),
        st.Page("pages/2_Timetable.py",             title="Timetable",             icon="📅"),
        st.Page("pages/3_Team_Meetings.py",          title="Team Meetings",         icon="👥"),
        st.Page("pages/5_Behaviour_Support.py",      title="Behaviour Support",     icon="📊"),
        st.Page("pages/7_Sensory_Overview.py",       title="Sensory Overview",      icon="🧠"),
        st.Page("pages/8_Sensory_Profile.py",        title="Sensory Profile",       icon="📋"),
        st.Page("pages/10_Document_Library.py",      title="Document Library",      icon="📁"),
        st.Page("pages/11_Digital_Staff_Meeting.py", title="Digital Staff Meeting", icon="🗓"),
        st.Page("pages/12_Calendar.py",              title="Calendar",              icon="📆"),
        st.Page("pages/13_Footy_Tipping.py",         title="Footy Tipping",         icon="🏈"),
        st.Page("pages/14_Committees.py",            title="Committees",            icon="🏛"),
    ],
    position="hidden",
)
pg.run()
