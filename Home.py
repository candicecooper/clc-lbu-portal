from theme import apply_clc_theme
import streamlit as st
from auth import require_auth, logout_button, get_staff_name

st.set_page_config(
    page_title="CLC LBU Staff Portal",
    page_icon="🏫",
    layout="wide",
)
apply_clc_theme()

require_auth("CLC LBU Staff Portal", "🏫")
logout_button("sidebar")



staff_name = get_staff_name()
from datetime import date
today = date.today().strftime("%A %-d %B %Y")

st.markdown(f"""
<div class="portal-header">
  <div>
    <div class="portal-title">🏫 CLC LBU Staff Portal</div>
    <div class="portal-sub">Cowandilla Learning Centre — Learning &amp; Behaviour Unit</div>
  </div>
  <div class="portal-staff">
    👋 Welcome, {staff_name}<br>
    <span style="font-size:11px;opacity:0.75;">{today}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── App definitions ───────────────────────────────────────────────────────────
APPS = {
    "Daily Operations": [
        {
            "icon": "📰",
            "title": "Daily Bulletin",
            "desc": "Vehicle bookings, staff notices, program changes, TRT workflow and printable bulletin.",
            "tag": "tag-ops",
            "tag_label": "Daily ops",
            "page": "1_Daily_Bulletin",
        },
        {
            "icon": "📅",
            "title": "Timetable",
            "desc": "JP, PY and SY timetables with SA school calendar term/week detection and PDF export.",
            "tag": "tag-ops",
            "tag_label": "Daily ops",
            "page": "Timetable",
        },
    ],
    "Staff & HR": [
        {
            "icon": "👥",
            "title": "Team Meetings",
            "desc": "Schedule, agenda, minutes, actions, attendance and documents for JP/PY/SY/Staff/Admin.",
            "tag": "tag-staff",
            "tag_label": "Staff & HR",
            "page": "Team_Meetings",
        },
        {
            "icon": "🗓",
            "title": "Staff Meeting",
            "desc": "Weekly staff meeting agenda submission, acknowledgements, polls and comments.",
            "tag": "tag-staff",
            "tag_label": "Staff & HR",
            "page": "Staff_Meeting",
        },
    ],
    "Safety & Behaviour": [
        {
            "icon": "📊",
            "title": "Behaviour Support",
            "desc": "Incident logging, ABCH forms, student dashboards, BAP generation and approval workflow.",
            "tag": "tag-safety",
            "tag_label": "Safety",
            "page": "Behaviour_Support",
        },
        {
            "icon": "📈",
            "title": "Engagement Tracker",
            "desc": "Log and analyse student engagement by support type with BSEM & PBIS hypothesis generation.",
            "tag": "tag-safety",
            "tag_label": "Safety",
            "page": "Engagement_Tracker",
        },
        {
            "icon": "🧠",
            "title": "Sensory Overview",
            "desc": "Whole-cohort sensory profile overview across programs and support needs.",
            "tag": "tag-safety",
            "tag_label": "Safety",
            "page": "Sensory_Overview",
        },
        {
            "icon": "📋",
            "title": "Sensory Profile",
            "desc": "Individual student sensory profile with recommendations and strategies.",
            "tag": "tag-safety",
            "tag_label": "Safety",
            "page": "Sensory_Profile",
        },
    ],
    "Governance": [
        {
            "icon": "📑",
            "title": "PAC Meeting Portal",
            "desc": "Personnel Advisory Committee procedures, checklists and progress tracking.",
            "tag": "tag-gov",
            "tag_label": "Governance",
            "page": "PAC_Meeting",
        },
    ],
}

# ── Render sections ───────────────────────────────────────────────────────────
for section, apps in APPS.items():
    st.markdown(f'<div class="section-label">{section}</div>', unsafe_allow_html=True)
    cols = st.columns(len(apps) if len(apps) <= 4 else 4)
    for i, app in enumerate(apps):
        with cols[i % 4]:
            # Use st.page_link for actual navigation
            with st.container():
                st.markdown(f"""
                <div class="app-card">
                  <div class="app-card-icon">{app["icon"]}</div>
                  <div class="app-card-title">{app["title"]}</div>
                  <div class="app-card-desc">{app["desc"]}</div>
                  <span class="app-card-tag {app["tag"]}">{app["tag_label"]}</span>
                </div>
                """, unsafe_allow_html=True)
                st.page_link(f"pages/{app['page']}.py", label=f"Open {app['title']} →",
                             use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.divider()
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    st.caption("🏫 Cowandilla Learning Centre — LBU")
with col_f2:
    st.caption(f"📅 {today}")
with col_f3:
    st.caption(f"👤 Logged in as {staff_name}")

