"""
CLC-LBU Quick Incident Log
──────────────────────────
Fast, no-login incident entry for regular (non-critical) incidents.
Writes directly to the same `incidents` table as the Behaviour Support Tool.
"""
import streamlit as st
import uuid
from datetime import date, datetime

st.set_page_config(
    page_title="Quick Incident Log — CLC LBU",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Supabase connection ───────────────────────────────────────────────────────
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

@st.cache_resource
def init_supabase():
    if not SUPABASE_AVAILABLE:
        return None
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception:
        return None

supabase = init_supabase()

# ── Data constants (match 5_Behaviour_Support.py exactly) ────────────────────
BEHAVIOUR_TYPES = [
    "--- REFUSAL / WITHDRAWAL ---",
    "Verbal refusal of instruction",
    "Task refusal / passive non-compliance",
    "Shutdown / complete withdrawal",
    "Selective mutism / non-responsiveness",
    "--- ESCAPE / EVASION ---",
    "Unsanctioned departure (elopement)",
    "Absconding from school grounds",
    "Hiding or avoiding adult proximity",
    "--- DISRUPTIVE BEHAVIOUR ---",
    "Inappropriate vocalisation / noises",
    "Disruptive verbal commentary",
    "Interrupting / calling out",
    "Property misuse or interference",
    "--- AGGRESSION ---",
    "Verbal aggression toward peer",
    "Verbal aggression toward adult",
    "Physical aggression toward peer",
    "Physical aggression toward adult",
    "Threatening behaviour",
    "--- PROPERTY ---",
    "Property destruction",
    "Throwing objects",
    "--- SELF-REGULATION ---",
    "Self-injurious behaviour",
    "Dysregulated emotional expression",
    "--- OTHER ---",
    "Other (specify in description)",
]

ANTECEDENTS = [
    "--- PEER ---",
    "Peer - negative peer feedback",
    "Peer - peer conflict/interaction",
    "Peer - participating in competition",
    "Peer - losing against a peer/s",
    "Peer - another student escalating",
    "--- TRANSITION ---",
    "Transition - to a non-preferred activity",
    "Transition - from one activity to another",
    "Transition - from one environment to another",
    "Transition - another teacher coming into the program",
    "Transition - from play/yard to classroom",
    "Transition - from home to the program",
    "Transition - off a device",
    "--- INSTRUCTIONS ---",
    "Instructions - following instructions given by an adult",
    "Instructions - following task demands",
    "--- ENGAGEMENT ---",
    "Engagement - engaging in a non-preferred learning area",
    "Engagement - having to wait",
    "Engagement - change in routine",
    "Engagement - learning task too difficult",
    "Engagement - having to work with a peer",
    "Engagement - working independently",
    "Engagement - interrupted activity",
    "Engagement - not being able to finish an activity",
    "--- SENSORY ---",
    "Sensory - crowded area",
    "Sensory - noise",
    "Sensory - environment too bright",
    "Sensory - no medication",
    "Sensory - hungry/thirsty",
    "Sensory - unable to take a movement break",
    "--- OTHER ---",
    "Other - perceived injustice",
    "Other - TRT (Temporary Relief Teacher)",
    "Other - incident before coming to program",
    "Other - verbalising not wanting to be at the program",
    "Other - staff attention shifted",
    "Other - unstructured time",
    "Other - access denied",
]

LOCATIONS = [
    "JP Room", "PY Room", "SY Room", "Yard", "Playground",
    "Library", "Kitchen", "Office", "Student Gate", "Toilets",
    "Transition area", "Other",
]

INTERVENTIONS = [
    "CPI Supportive stance",
    "Offered break",
    "Reduced demand",
    "Provided choices",
    "Removed audience",
    "Visual supports",
    "Co-regulation",
    "Prompted coping skill",
    "Redirection",
]

SESSIONS = {
    "Morning (before 11:00am)": "Morning",
    "Middle of day (11:00am – 1:30pm)": "Middle",
    "Afternoon (1:31pm – 2:45pm)": "Afternoon",
}

SEVERITY_LABELS = {
    1: "1 — Low level, student coping",
    2: "2 — Escalating, still coping",
    3: "3 — Elevated, approaching edge of window",
    4: "4 — Outside window, significant dysregulation",
    5: "5 — Crisis, immediate safety concern",
}

SEVERITY_COLOURS = {1: "#22c55e", 2: "#eab308", 3: "#f97316", 4: "#ef4444", 5: "#7f1d1d"}

# ── Load students live from Supabase ─────────────────────────────────────────
@st.cache_data(ttl=120)
def load_students():
    if not supabase:
        return []
    try:
        resp = supabase.table("students").select(
            "id,first_name,last_name,name,program"
        ).eq("archived", False).execute()
        students = []
        for row in resp.data:
            full = (
                f"{row.get('first_name','')} {row.get('last_name','')}".strip()
                if row.get("first_name") else row.get("name", "Unknown")
            )
            students.append({
                "id": str(row["id"]),
                "name": full,
                "program": row.get("program", ""),
            })
        return sorted(students, key=lambda s: s["name"])
    except Exception:
        return []

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(
    "<div style='background:#1A7A7A;border-radius:12px;padding:1rem 1.5rem;"
    "margin-bottom:1.25rem;'>"
    "<div style='color:white;font-size:1.5rem;font-weight:700;'>⚡ Quick Incident Log</div>"
    "<div style='color:#fef3c7;font-size:.88rem;margin-top:.2rem;'>"
    "Cowandilla Learning Centre — Learning & Behaviour Unit</div>"
    "</div>",
    unsafe_allow_html=True,
)
st.caption(
    "Log a regular (non-critical) incident quickly. "
    "All entries appear immediately in the student's analysis in the Behaviour Support Tool. "
    "For critical incidents that require an ABCH form, use the full Behaviour Support Tool instead."
)

# ── Connection check ──────────────────────────────────────────────────────────
if not supabase:
    st.error(
        "⚠️ Database not connected — unable to save incidents. "
        "Check your Supabase credentials in Settings."
    )
    st.stop()

students = load_students()
if not students:
    st.warning("No students found in the database. Check the connection or add students via the portal.")
    st.stop()

# ── Form ──────────────────────────────────────────────────────────────────────
with st.form("quick_log_form", clear_on_submit=True):

    # ── Student + Staff row
    f_col1, f_col2 = st.columns([3, 2])
    with f_col1:
        student_options = {s["id"]: f"{s['name']}  ({s['program']})" for s in students}
        selected_id = st.selectbox(
            "👤 Student *",
            list(student_options.keys()),
            format_func=lambda x: student_options[x],
        )
    with f_col2:
        reported_by = st.text_input(
            "🙋 Your name *",
            placeholder="e.g. Sarah",
        )

    st.markdown("<hr style='margin:.6rem 0;border-color:#e2e8f0;'>", unsafe_allow_html=True)

    # ── Date / Time / Session row
    d_col1, d_col2, d_col3 = st.columns(3)
    with d_col1:
        inc_date = st.date_input("📅 Date *", value=date.today())
    with d_col2:
        inc_time = st.time_input("🕐 Approximate time *", value=datetime.now().replace(second=0, microsecond=0).time())
    with d_col3:
        session_label = st.selectbox("⏰ Session *", list(SESSIONS.keys()))

    # ── Location
    location = st.selectbox("📍 Location *", LOCATIONS)

    st.markdown("<hr style='margin:.6rem 0;border-color:#e2e8f0;'>", unsafe_allow_html=True)

    # ── Antecedent (what happened just before)
    st.markdown(
        "<div style='font-weight:600;color:#1e293b;font-size:.9rem;margin-bottom:.2rem;'>"
        "⚡ What happened just before? (Antecedent / Trigger) *</div>",
        unsafe_allow_html=True
    )
    ant_opts = [a for a in ANTECEDENTS if not a.startswith("---")]
    antecedent = st.selectbox(
        "Select the closest match",
        ANTECEDENTS,
        label_visibility="collapsed",
    )

    # ── Behaviour
    st.markdown(
        "<div style='font-weight:600;color:#1e293b;font-size:.9rem;margin:.5rem 0 .2rem;'>"
        "🎯 Behaviour observed *</div>",
        unsafe_allow_html=True
    )
    beh_opts = BEHAVIOUR_TYPES
    behaviour = st.selectbox(
        "Select behaviour",
        beh_opts,
        label_visibility="collapsed",
    )

    st.markdown("<hr style='margin:.6rem 0;border-color:#e2e8f0;'>", unsafe_allow_html=True)

    # ── Severity
    st.markdown(
        "<div style='font-weight:600;color:#1e293b;font-size:.9rem;margin-bottom:.4rem;'>"
        "📊 Severity *</div>",
        unsafe_allow_html=True,
    )
    sev_col1, sev_col2 = st.columns([2, 3])
    with sev_col1:
        severity = st.select_slider(
            "Severity",
            options=[1, 2, 3, 4, 5],
            value=2,
            label_visibility="collapsed",
        )
    with sev_col2:
        _sc = SEVERITY_COLOURS[severity]
        st.markdown(
            f"<div style='background:{_sc}20;border-left:4px solid {_sc};"
            f"border-radius:6px;padding:.4rem .75rem;font-size:.85rem;"
            f"color:#1e293b;margin-top:.1rem;'>"
            f"<b>{SEVERITY_LABELS[severity]}</b></div>",
            unsafe_allow_html=True,
        )
    st.caption(
        "🟡 1–2 = Coping zone (behaviour present, student managing)  ·  "
        "🟠 3 = Approaching edge  ·  🔴 4–5 = Outside window"
    )

    st.markdown("<hr style='margin:.6rem 0;border-color:#e2e8f0;'>", unsafe_allow_html=True)

    # ── Staff response
    st.markdown(
        "<div style='font-weight:600;color:#1e293b;font-size:.9rem;margin-bottom:.2rem;'>"
        "🤝 Staff response / intervention *</div>",
        unsafe_allow_html=True,
    )
    interventions = st.multiselect(
        "Select all that apply",
        INTERVENTIONS,
        label_visibility="collapsed",
    )

    # ── Duration + Description (optional)
    opt_col1, opt_col2 = st.columns([1, 2])
    with opt_col1:
        duration = st.number_input(
            "⏱️ Duration (minutes)",
            min_value=0, max_value=120, value=0, step=1,
            help="Leave 0 if unknown",
        )
    with opt_col2:
        description = st.text_area(
            "📝 Brief notes (optional)",
            height=80,
            placeholder="Any additional context not captured above...",
        )

    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

    # ── Submit
    submitted = st.form_submit_button(
        "✅ Log Incident",
        type="primary",
        use_container_width=True,
    )

# ── Validation + Save ─────────────────────────────────────────────────────────
if submitted:
    errors = []
    if not reported_by.strip():
        errors.append("Please enter your name.")
    if antecedent.startswith("---"):
        errors.append("Please select an antecedent (not a category header).")
    if behaviour.startswith("---"):
        errors.append("Please select a behaviour (not a category header).")
    if not interventions:
        errors.append("Please select at least one staff response / intervention.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        inc_day = inc_date.strftime("%A")
        session_val = SESSIONS[session_label]

        # Look up staff ID if possible
        staff_id = None
        try:
            staff_resp = supabase.table("staff").select("id").eq("name", reported_by.strip()).limit(1).execute()
            if staff_resp.data:
                staff_id = str(staff_resp.data[0]["id"])
        except Exception:
            pass

        incident = {
            "id":                 str(uuid.uuid4()),
            "student_id":         selected_id,
            "date":               inc_date.isoformat(),
            "time":               inc_time.strftime("%H:%M:%S"),
            "day":                inc_day,
            "session":            session_val,
            "location":           location,
            "behaviour_type":     behaviour,
            "antecedent":         antecedent,
            "intervention":       interventions,
            "severity":           severity,
            "reported_by":        staff_id,
            "description":        description.strip(),
            "duration_minutes":   duration if duration > 0 else None,
            "hypothesis_function": None,
            "hypothesis_item":    None,
            "is_critical":        False,
        }

        try:
            data = {
                "id":               incident["id"],
                "student_id":       incident["student_id"],
                "date":             incident["date"],
                "time":             incident["time"],
                "day_of_week":      incident["day"],
                "session":          incident["session"],
                "location":         incident["location"],
                "behaviour_type":   incident["behaviour_type"],
                "antecedent":       incident["antecedent"],
                "intervention":     incident["intervention"],
                "severity":         incident["severity"],
                "reported_by":      incident["reported_by"],
                "description":      incident["description"],
                "duration_minutes": incident["duration_minutes"],
                "hypothesis_function": None,
                "hypothesis_item":  None,
                "is_critical":      False,
            }
            supabase.table("incidents").insert(data).execute()

            student_name = student_options[selected_id].split("  (")[0]
            sev_col = SEVERITY_COLOURS[severity]
            st.markdown(
                f"<div style='background:#f0fdf4;border:2px solid #22c55e;border-radius:12px;"
                f"padding:1.1rem 1.5rem;margin-top:.5rem;'>"
                f"<div style='font-weight:700;color:#15803d;font-size:1rem;margin-bottom:.4rem;'>"
                f"✅ Incident logged successfully</div>"
                f"<div style='font-size:.85rem;color:#1e293b;line-height:1.7;'>"
                f"<b>Student:</b> {student_name}<br>"
                f"<b>Date/Time:</b> {inc_date.strftime('%-d %b %Y')} at {inc_time.strftime('%H:%M')}"
                f" — {session_label}<br>"
                f"<b>Location:</b> {location}<br>"
                f"<b>Behaviour:</b> {behaviour}<br>"
                f"<b>Antecedent:</b> {antecedent}<br>"
                f"<b>Severity:</b> <span style='background:{sev_col};color:white;padding:.1rem .4rem;"
                f"border-radius:4px;font-size:.82rem;'>{SEVERITY_LABELS[severity]}</span><br>"
                f"<b>Logged by:</b> {reported_by.strip()}"
                f"</div></div>",
                unsafe_allow_html=True,
            )
            st.caption("The incident is now visible in the Behaviour Support Tool analysis for this student.")

        except Exception as e:
            st.error(f"❌ Save failed: {e}")
            st.caption("Check your Supabase connection or contact the portal administrator.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align:center;font-size:.75rem;color:#94a3b8;'>"
    "CLC-LBU Portal · Quick Incident Log · "
    "For critical incidents use the full Behaviour Support Tool"
    "</div>",
    unsafe_allow_html=True,
)
