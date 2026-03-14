import streamlit as st
from supabase import create_client
import json
from datetime import date, datetime

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sensory Profiles",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_clc_theme()

from auth import require_auth, logout_button, get_staff_name
from theme import apply_clc_theme
require_auth("Sensory Profiles", "🧠")
logout_button("sidebar")

TEAL  = "#1A7A7A"
AMBER = "#C8760A"

# ── UPDATE this to your deployed portal URL once live ─────────────────────────
# Used for "New Overview" deep-links (pre-selects the student in Sensory Overview)
# Format: https://your-portal-app.streamlit.app/Sensory_Overview
SENSORY_OVERVIEW_APP_URL = "https://your-portal-app.streamlit.app/Sensory_Overview"


# ── Supabase ───────────────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = get_supabase()

# ── Constants ──────────────────────────────────────────────────────────────────
SECTION_ICONS = {
    "Body Awareness (Interoception)": "🫀",
    "Visual":                         "👁️",
    "Sense of Body in Space":         "🗺️",
    "Auditory":                       "👂",
    "Auditory Processing":            "🔊",
    "Smell":                          "👃",
    "Touch and Textures":             "🤚",
    "Kinaesthetic":                   "🏃",
}

PROGRAM_LABELS = {"JP": "Junior Primary", "PY": "Primary Years", "SY": "Senior Years"}

# ── Helpers ────────────────────────────────────────────────────────────────────
def priority_info(pct):
    if pct >= 60:
        return "HIGH PRIORITY",   "high", "🔴"
    elif pct >= 30:
        return "MEDIUM PRIORITY", "med",  "🟡"
    return "LOW PRIORITY",        "low",  "🟢"


def pri_card(section_name, info, icon=""):
    return f"""
    <div class="pri-card {info['css']}">
        <div class="plabel">{icon} {section_name}</div>
        <div class="pval">{info['emoji']} {info['priority']}</div>
        <div class="psub">{info['checked']}/{info['total']} ({info['pct']}%)</div>
    </div>"""


def prog_badge(program):
    css = program.lower() if program in ("JP", "PY", "SY") else ""
    return f'<span class="prog-badge {css}">{program}</span>'


# ── Data loaders ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_students():
    try:
        res = supabase.table("students") \
            .select("id,name,edid,program,grade,dob") \
            .eq("archived", False) \
            .order("name").execute()
        return res.data or []
    except Exception as e:
        st.error(f"Could not load students: {e}")
        return []


@st.cache_data(ttl=30)
def load_latest_overview(student_id: str):
    try:
        res = supabase.table("sensory_overviews") \
            .select("id,overview_date,review_date,completed_by,priority_results,responses") \
            .eq("student_id", student_id) \
            .order("overview_date", desc=True) \
            .limit(1).execute()
        return res.data[0] if res.data else None
    except Exception:
        return None


@st.cache_data(ttl=30)
def load_all_overviews_for_student(student_id: str):
    try:
        res = supabase.table("sensory_overviews") \
            .select("id,overview_date,review_date,completed_by,priority_results,responses") \
            .eq("student_id", student_id) \
            .order("overview_date", desc=True).execute()
        return res.data or []
    except Exception:
        return []


def parse_priorities(raw):
    if not raw:
        return {}
    try:
        if isinstance(raw, str):
            raw = json.loads(raw)
        out = {}
        for sec, info in raw.items():
            _, css, emoji = priority_info(info.get("pct", 0))
            out[sec] = {**info, "css": css, "emoji": emoji}
        return out
    except Exception:
        return {}


def parse_responses(raw):
    if not raw:
        return {}
    try:
        if isinstance(raw, str):
            return json.loads(raw)
        return raw
    except Exception:
        return {}


def review_status(review_date_str):
    if not review_date_str:
        return "No review date set", "#888"
    try:
        rv = date.fromisoformat(review_date_str)
        delta = (rv - date.today()).days
        if delta < 0:
            return f"⚠️ Review overdue ({abs(delta)} days)", "#c62828"
        elif delta <= 14:
            return f"🟡 Review due soon ({delta} days)", "#e65100"
        else:
            return f"🟢 Review due {rv.strftime('%d %b %Y')}", "#2e7d32"
    except Exception:
        return review_date_str, "#555"


# ── Page header ────────────────────────────────────────────────────────────────
st.markdown("<h1>🧠 Sensory Profiles</h1>", unsafe_allow_html=True)
st.caption("View sensory overviews for all students. Linked to the Sensory Overview app and Behaviour Support data.")

students = load_students()

if not students:
    st.warning("No students found. Make sure students have been added via the Behaviour Support app or Sensory Overview app.")
    st.stop()

# ── Top controls ───────────────────────────────────────────────────────────────
ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 2])
with ctrl1:
    program_filter = st.selectbox(
        "Program",
        ["All Programs", "JP — Junior Primary", "PY — Primary Years", "SY — Senior Years"],
    )
with ctrl2:
    overview_filter = st.selectbox(
        "Overview status",
        ["All students", "Has overview", "No overview yet", "Review overdue"],
    )
with ctrl3:
    search_name = st.text_input("Search student name", placeholder="Type to filter…")

program_code = None
if "JP" in program_filter:
    program_code = "JP"
elif "PY" in program_filter:
    program_code = "PY"
elif "SY" in program_filter:
    program_code = "SY"

if program_code:
    students = [s for s in students if s.get("program") == program_code]
if search_name:
    students = [s for s in students if search_name.lower() in s["name"].lower()]

overview_map = {}
for s in students:
    overview_map[s["id"]] = load_latest_overview(s["id"])

if overview_filter == "Has overview":
    students = [s for s in students if overview_map.get(s["id"])]
elif overview_filter == "No overview yet":
    students = [s for s in students if not overview_map.get(s["id"])]
elif overview_filter == "Review overdue":
    def is_overdue(s):
        ov = overview_map.get(s["id"])
        if not ov:
            return False
        rv = ov.get("review_date")
        if not rv:
            return False
        try:
            return date.fromisoformat(rv) < date.today()
        except Exception:
            return False
    students = [s for s in students if is_overdue(s)]

st.markdown(f"**{len(students)} student{'s' if len(students) != 1 else ''}** matching filters")
st.markdown("---")

# ── Student list ───────────────────────────────────────────────────────────────
if not students:
    st.info("No students match the current filters.")
    st.stop()

for student in students:
    sid      = student["id"]
    sname    = student["name"]
    program  = student.get("program", "—")
    grade    = student.get("grade", "—")
    edid     = student.get("edid", "—")
    overview = overview_map.get(sid)

    pills_html = ""
    if overview:
        pr = parse_priorities(overview.get("priority_results"))
        for sec, info in pr.items():
            icon = SECTION_ICONS.get(sec, "")
            pills_html += f'<span class="pill {info["css"]}">{icon} {sec.split("(")[0].strip()}</span> '
    else:
        pills_html = '<span class="pill none">No overview on file</span>'

    with st.expander(
        f"{'🔴 ' if overview and any(parse_priorities(overview.get('priority_results', {})).get(s, {}).get('priority') == 'HIGH PRIORITY' for s in SECTION_ICONS) else ''}"
        f"{sname}  ·  {program}  ·  {grade}  ·  {edid}",
        expanded=False,
    ):
        mc1, mc2 = st.columns([3, 1])
        with mc1:
            st.markdown(
                f'<div class="student-card">'
                f'<div class="sname">{sname} {prog_badge(program)}</div>'
                f'<div class="smeta">Grade: {grade} &nbsp;·&nbsp; EDID: {edid}</div>'
                f'<div style="margin-top:6px;">{pills_html}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with mc2:
            st.markdown("&nbsp;")
            st.link_button(
                "➕ New Overview",
                f"{SENSORY_OVERVIEW_APP_URL}?student_id={sid}",
                use_container_width=True,
            )

        if not overview:
            st.markdown(
                f'<div class="no-overview">'
                f'⚠️ No sensory overview has been completed for <strong>{sname}</strong> yet.<br>'
                f'Click <strong>New Overview</strong> above to start one — the student will be pre-selected.'
                f'</div>',
                unsafe_allow_html=True,
            )
            continue

        ov_date  = overview.get("overview_date", "—")
        rev_date = overview.get("review_date")
        by       = overview.get("completed_by", "—")
        rev_label, rev_colour = review_status(rev_date)

        st.markdown(
            f'<div class="ov-meta">'
            f'📅 Overview: <strong>{ov_date}</strong> &nbsp;·&nbsp; '
            f'Completed by: <strong>{by}</strong> &nbsp;·&nbsp; '
            f'<span style="color:{rev_colour};font-weight:700;">{rev_label}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        tab_summary, tab_detail, tab_history = st.tabs(
            ["📊 Priority Summary", "✅ Checked Items", "🕓 History"]
        )

        with tab_summary:
            pr = parse_priorities(overview.get("priority_results"))
            if not pr:
                st.warning("No priority data available.")
            else:
                high_secs = [(s, i) for s, i in pr.items() if i.get("priority") == "HIGH PRIORITY"]
                med_secs  = [(s, i) for s, i in pr.items() if i.get("priority") == "MEDIUM PRIORITY"]
                low_secs  = [(s, i) for s, i in pr.items() if i.get("priority") == "LOWER PRIORITY"]

                if high_secs:
                    st.markdown("##### 🔴 High Priority")
                    hcols = st.columns(min(len(high_secs), 4))
                    for idx, (sec, info) in enumerate(high_secs):
                        with hcols[idx % 4]:
                            st.markdown(pri_card(sec, info, SECTION_ICONS.get(sec, "")), unsafe_allow_html=True)

                if med_secs:
                    st.markdown("##### 🟡 Medium Priority")
                    mcols = st.columns(min(len(med_secs), 4))
                    for idx, (sec, info) in enumerate(med_secs):
                        with mcols[idx % 4]:
                            st.markdown(pri_card(sec, info, SECTION_ICONS.get(sec, "")), unsafe_allow_html=True)

                if low_secs:
                    st.markdown("##### 🟢 Low Priority")
                    lcols = st.columns(min(len(low_secs), 4))
                    for idx, (sec, info) in enumerate(low_secs):
                        with lcols[idx % 4]:
                            st.markdown(pri_card(sec, info, SECTION_ICONS.get(sec, "")), unsafe_allow_html=True)

        with tab_detail:
            responses = parse_responses(overview.get("responses"))
            if not responses:
                st.info("No response detail available.")
            else:
                any_checked = False
                for sec_name, items_dict in responses.items():
                    icon          = SECTION_ICONS.get(sec_name, "")
                    checked_items = [it for it, val in items_dict.items() if val]
                    if not checked_items:
                        continue
                    any_checked = True
                    _, css, emoji = priority_info(
                        round(len(checked_items) / max(len(items_dict), 1) * 100, 1)
                    )
                    st.markdown(f"**{icon} {sec_name}** {emoji}")
                    ic1, ic2 = st.columns(2)
                    for i, item in enumerate(checked_items):
                        with [ic1, ic2][i % 2]:
                            st.markdown(f"✅ {item}")
                    st.markdown("---")
                if not any_checked:
                    st.info("No items were checked in this overview.")

        with tab_history:
            all_overviews = load_all_overviews_for_student(sid)
            if len(all_overviews) <= 1:
                st.info("Only one overview on file — history will appear here as more are added.")
            else:
                for ov in all_overviews:
                    o_date = ov.get("overview_date", "—")
                    o_by   = ov.get("completed_by", "—")
                    o_rev  = ov.get("review_date", "—")
                    with st.expander(f"📄 {o_date}  ·  {o_by}", expanded=False):
                        st.caption(f"Review date: {o_rev}")
                        hist_pr = parse_priorities(ov.get("priority_results"))
                        if hist_pr:
                            hc = st.columns(4)
                            for idx, (sec, info) in enumerate(hist_pr.items()):
                                with hc[idx % 4]:
                                    st.markdown(
                                        pri_card(sec, info, SECTION_ICONS.get(sec, "")),
                                        unsafe_allow_html=True,
                                    )

        st.markdown("---")
        fa1, fa2 = st.columns(2)
        with fa1:
            st.link_button(
                "🔄 Start updated overview",
                f"{SENSORY_OVERVIEW_APP_URL}?student_id={sid}",
                use_container_width=True,
            )
        with fa2:
            st.link_button(
                "📋 Go to Sensory Overview",
                SENSORY_OVERVIEW_APP_URL,
                use_container_width=True,
            )
