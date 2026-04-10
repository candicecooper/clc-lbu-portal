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

TEAL  = "#1A7A7A"
AMBER = "#C8760A"

# ── UPDATE THIS to your deployed sensory overview app URL ──────────────────────
SENSORY_OVERVIEW_APP_URL = "https://your-sensory-overview-app.streamlit.app"

st.markdown(f"""
<style>
    .stApp {{ background-color: #f5f7f7; }}
    h1, h2, h3 {{ color: {TEAL}; }}

    /* Student card */
    .student-card {{
        background: white;
        border-radius: 10px;
        border-left: 6px solid {TEAL};
        padding: 14px 18px;
        margin-bottom: 10px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.07);
    }}
    .student-card .sname  {{ font-size: 1.1rem; font-weight: 700; color: {TEAL}; }}
    .student-card .smeta  {{ font-size: 0.8rem; color: #666; margin-top: 2px; }}

    /* Priority pills */
    .pill {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 700;
        margin: 2px 2px;
    }}
    .pill.high {{ background: #fde8e8; color: #c62828; }}
    .pill.med  {{ background: #fff3e0; color: #e65100; }}
    .pill.low  {{ background: #e8f5e9; color: #2e7d32; }}
    .pill.none {{ background: #eeeeee; color: #555; }}

    /* Priority breakdown cards */
    .pri-card {{
        padding: 10px 14px;
        border-radius: 8px;
        margin: 4px 0;
        background: white;
        border-left: 5px solid #ccc;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }}
    .pri-card.high {{ border-left-color: #c62828; background: #fff8f8; }}
    .pri-card.med  {{ border-left-color: #e65100; background: #fffaf5; }}
    .pri-card.low  {{ border-left-color: #2e7d32; background: #f6fff6; }}
    .pri-card .plabel {{ font-size: 0.72rem; font-weight: 700; color: #555; }}
    .pri-card .pval   {{ font-size: 1rem;   font-weight: 800; }}
    .pri-card.high .pval {{ color: #c62828; }}
    .pri-card.med  .pval {{ color: #e65100; }}
    .pri-card.low  .pval {{ color: #2e7d32; }}
    .pri-card .psub  {{ font-size: 0.7rem; color: #888; }}

    /* No overview banner */
    .no-overview {{
        background: #fff8e1;
        border: 2px dashed {AMBER};
        border-radius: 8px;
        padding: 14px;
        color: #7a5800;
        font-size: 0.9rem;
    }}

    /* Overview meta bar */
    .ov-meta {{
        background: #e8f4f4;
        border-radius: 6px;
        padding: 8px 14px;
        font-size: 0.82rem;
        color: #2a5a5a;
        margin-bottom: 10px;
    }}

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {{ gap: 4px; }}
    .stTabs [data-baseweb="tab"] {{
        background: #e0ecec; border-radius: 6px 6px 0 0;
        color: {TEAL}; font-weight: 600;
    }}
    .stTabs [aria-selected="true"] {{ background: {TEAL} !important; color: white !important; }}

    /* Program badge */
    .prog-badge {{
        display: inline-block;
        background: {TEAL};
        color: white;
        padding: 2px 9px;
        border-radius: 10px;
        font-size: 0.75rem;
        font-weight: 700;
    }}
    .prog-badge.jp {{ background: #1565c0; }}
    .prog-badge.py {{ background: #6a1b9a; }}
    .prog-badge.sy {{ background: {TEAL};  }}
</style>
""", unsafe_allow_html=True)

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
def load_all_overviews():
    """Load all overviews, grouped by student_name."""
    try:
        res = supabase.table("sensory_overviews") \
            .select("id,student_id,student_name,overview_date,review_date,completed_by,priority_results,responses") \
            .order("overview_date", desc=True).execute()
        return res.data or []
    except Exception as e:
        st.error(f"Could not load overviews: {e}")
        return []


def build_student_list(all_overviews):
    """
    Derive a unique student list from saved overviews.
    Returns list of dicts: {name, program, latest_overview, all_overviews}
    """
    seen = {}
    for ov in all_overviews:
        name = ov.get("student_name", "Unknown")
        if name not in seen:
            seen[name] = {"name": name, "overviews": []}
        seen[name]["overviews"].append(ov)
    # Sort each student's overviews newest-first (already sorted from query)
    result = []
    for name, data in seen.items():
        result.append({
            "name":           name,
            "latest_overview": data["overviews"][0],
            "all_overviews":  data["overviews"],
        })
    return sorted(result, key=lambda x: x["name"])


def parse_priorities(raw):
    if not raw:
        return {}
    try:
        if isinstance(raw, str):
            raw = json.loads(raw)
        # Annotate with css/emoji
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
    """Returns (label, colour) based on review date."""
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
st.caption("View sensory overviews for all students.")

all_overviews = load_all_overviews()

if not all_overviews:
    st.info("No overviews have been saved yet. Complete a Sensory Overview first.")
    st.link_button("➕ Go to Sensory Overview", SENSORY_OVERVIEW_APP_URL)
    st.stop()

students = build_student_list(all_overviews)

# ── Top controls ───────────────────────────────────────────────────────────────
ctrl1, ctrl2 = st.columns([2, 2])
with ctrl1:
    overview_filter = st.selectbox(
        "Overview status",
        ["All students", "Review overdue", "Review due soon"],
    )
with ctrl2:
    search_name = st.text_input("Search student name", placeholder="Type to filter…")

if search_name:
    students = [s for s in students if search_name.lower() in s["name"].lower()]

# Apply overview status filter
if overview_filter == "Review overdue":
    def is_overdue(s):
        rv = s["latest_overview"].get("review_date")
        if not rv:
            return False
        try:
            return date.fromisoformat(rv) < date.today()
        except Exception:
            return False
    students = [s for s in students if is_overdue(s)]
elif overview_filter == "Review due soon":
    def is_due_soon(s):
        rv = s["latest_overview"].get("review_date")
        if not rv:
            return False
        try:
            delta = (date.fromisoformat(rv) - date.today()).days
            return 0 <= delta <= 14
        except Exception:
            return False
    students = [s for s in students if is_due_soon(s)]

st.markdown(f"**{len(students)} student{'s' if len(students) != 1 else ''}** matching filters")
st.markdown("---")

if not students:
    st.info("No students match the current filters.")
    st.stop()

# ── Student list ───────────────────────────────────────────────────────────────
for student in students:
    sname    = student["name"]
    overview = student["latest_overview"]
    all_ovs  = student["all_overviews"]

    # Build priority pills
    pills_html = ""
    pr = parse_priorities(overview.get("priority_results"))
    for sec, info in pr.items():
        icon = SECTION_ICONS.get(sec, "")
        pills_html += f'<span class="pill {info["css"]}">{icon} {sec.split("(")[0].strip()}</span> '

    has_high = any(i.get("priority") == "HIGH PRIORITY" for i in pr.values())
    ov_date  = overview.get("overview_date", "—")
    by       = overview.get("completed_by", "—")

    with st.expander(
        f"{'🔴 ' if has_high else ''}{sname}  ·  Last overview: {ov_date}  ·  {by}",
        expanded=False,
    ):
        # ── Student meta bar ───────────────────────────────────────────────────
        mc1, mc2 = st.columns([3, 1])
        with mc1:
            st.markdown(
                f'<div class="student-card">'
                f'<div class="sname">{sname}</div>'
                f'<div style="margin-top:6px;">{pills_html}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with mc2:
            st.markdown("&nbsp;")
            st.link_button(
                "➕ New Overview",
                f"{SENSORY_OVERVIEW_APP_URL}?student_name={sname}",
                use_container_width=True,
            )

        # ── Overview meta ──────────────────────────────────────────────────────
        rev_date  = overview.get("review_date")
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

        # ── SUMMARY tab ───────────────────────────────────────────────────────
        with tab_summary:
            pr = parse_priorities(overview.get("priority_results"))
            if not pr:
                st.warning("No priority data available.")
            else:
                high_secs = [(s, i) for s, i in pr.items() if i.get("priority") == "HIGH PRIORITY"]
                med_secs  = [(s, i) for s, i in pr.items() if i.get("priority") == "MEDIUM PRIORITY"]
                low_secs  = [(s, i) for s, i in pr.items() if i.get("priority") == "LOW PRIORITY"]

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

        # ── CHECKED ITEMS tab ─────────────────────────────────────────────────
        with tab_detail:
            responses = parse_responses(overview.get("responses"))
            if not responses:
                st.info("No response detail available.")
            else:
                any_checked = False
                for sec_name, items_dict in responses.items():
                    icon         = SECTION_ICONS.get(sec_name, "")
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

        # ── HISTORY tab ───────────────────────────────────────────────────────
        with tab_history:
            if len(all_ovs) <= 1:
                st.info("Only one overview on file — history will appear here as more are added.")
            else:
                for ov in all_ovs:
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

        # ── Footer actions ─────────────────────────────────────────────────────
        st.markdown("---")
        fa1, fa2 = st.columns(2)
        with fa1:
            st.link_button(
                "🔄 Start updated overview",
                f"{SENSORY_OVERVIEW_APP_URL}?student_name={sname}",
                use_container_width=True,
            )
        with fa2:
            st.link_button(
                "📋 Go to Sensory Overview app",
                SENSORY_OVERVIEW_APP_URL,
                use_container_width=True,
            )
