from theme import apply_clc_theme
import streamlit as st
from auth import require_auth, logout_button, get_staff_name

st.set_page_config(
    page_title="CLC LBU Staff Portal",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_clc_theme()
require_auth("CLC LBU Staff Portal", "🏫")
logout_button("sidebar")

staff_name = get_staff_name()
from datetime import date
today = date.today().strftime("%A %-d %B %Y")

APPS = {
    "Daily Operations": [
        {"icon": "📰", "title": "Daily Bulletin", "desc": "Vehicle bookings, staff notices, program changes, TRT workflow and printable bulletin.", "tag": "tag-ops", "tag_label": "Daily ops", "page": "1_Daily_Bulletin"},
        {"icon": "📅", "title": "Timetable", "desc": "JP, PY and SY timetables.", "tag": "tag-ops", "tag_label": "Daily ops", "page": "2_Timetable"},
    ],
    "Staff & HR": [
        {"icon": "👥", "title": "Team Meetings", "desc": "Schedule, agenda, minutes and actions.", "tag": "tag-staff", "tag_label": "Staff & HR", "page": "3_Team_Meetings"},
        {"icon": "🗓", "title": "Digital Staff Meeting", "desc": "Weekly staff meeting agenda, acknowledgements and polls.", "tag": "tag-staff", "tag_label": "Staff & HR", "page": "11_Digital_Staff_Meeting"},
    ],
    "Safety & Behaviour": [
        {"icon": "📊", "title": "Behaviour Support", "desc": "Incident logging, ABCH forms, student dashboards and BAP generation.", "tag": "tag-safety", "tag_label": "Safety", "page": "5_Behaviour_Support"},
        {"icon": "🧠", "title": "Sensory Overview", "desc": "Whole-cohort sensory profile overview.", "tag": "tag-safety", "tag_label": "Safety", "page": "7_Sensory_Overview"},
        {"icon": "📋", "title": "Sensory Profile", "desc": "Individual student sensory profile.", "tag": "tag-safety", "tag_label": "Safety", "page": "8_Sensory_Profile"},
    ],
    "Tools & Governance": [
        {"icon": "📁", "title": "Document Library", "desc": "Shared document storage.", "tag": "tag-ops", "tag_label": "Tools", "page": "10_Document_Library"},
        {"icon": "📆", "title": "Calendar", "desc": "School and LBU calendar.", "tag": "tag-ops", "tag_label": "Tools", "page": "12_Calendar"},
        {"icon": "🏈", "title": "Footy Tipping", "desc": "AFL tipping competition.", "tag": "tag-ops", "tag_label": "Tools", "page": "13_Footy_Tipping"},
        {"icon": "🏛", "title": "Committees", "desc": "Committee membership and meetings.", "tag": "tag-gov", "tag_label": "Governance", "page": "14_Committees"},
    ],
}

for section, apps in APPS.items():
    st.markdown(f'<div class="section-label">{section}</div>', unsafe_allow_html=True)
    cols = st.columns(min(len(apps), 4))
    for i, app in enumerate(apps):
        with cols[i % 4]:
            st.markdown(f"""
            <div class="app-card">
              <div class="app-card-icon">{app["icon"]}</div>
              <div class="app-card-title">{app["title"]}</div>
              <div class="app-card-desc">{app["desc"]}</div>
            </div>
            """, unsafe_allow_html=True)
            st.page_link(f"pages/{app['page']}.py", label=f"Open {app['title']} →", use_container_width=True)

st.divider()
st.caption(f"🏫 Cowandilla Learning Centre — LBU · {today} · 👤 {staff_name}")
