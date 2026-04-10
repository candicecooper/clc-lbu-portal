import streamlit as st
from supabase import create_client
import json
from datetime import date

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sensory Overview",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

TEAL  = "#1A7A7A"
AMBER = "#C8760A"

st.markdown(f"""
<style>
    .stApp {{ background-color: #f5f7f7; }}
    h1 {{ color: {TEAL}; }}
    .section-header {{
        background: {TEAL}; color: white;
        padding: 8px 14px; border-radius: 6px;
        font-weight: 700; font-size: 1rem; margin-bottom: 6px;
    }}
    .priority-card {{
        padding: 10px 14px; border-radius: 6px; margin: 4px 0;
        background: white; border-left: 5px solid #ccc;
    }}
    .priority-card.high {{ border-left-color: #c62828; }}
    .priority-card.med  {{ border-left-color: #e65100; }}
    .priority-card.low  {{ border-left-color: #2e7d32; }}
    .priority-card .label {{ font-size: 0.75rem; font-weight: 700; color: #444; }}
    .priority-card .pval  {{ font-size: 1.1rem; font-weight: 800; }}
    .priority-card.high .pval {{ color: #c62828; }}
    .priority-card.med  .pval {{ color: #e65100; }}
    .priority-card.low  .pval {{ color: #2e7d32; }}
    .priority-card .sub {{ font-size: 0.75rem; color: #666; }}
    .student-badge {{
        background: {TEAL}; color: white;
        padding: 6px 14px; border-radius: 20px;
        font-weight: 700; display: inline-block; margin-bottom: 8px;
    }}
    div[data-testid="stCheckbox"] label {{ font-size: 0.9rem; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 4px; }}
    .stTabs [data-baseweb="tab"] {{
        background: #e0ecec; border-radius: 6px 6px 0 0;
        color: {TEAL}; font-weight: 600;
    }}
    .stTabs [aria-selected="true"] {{ background: {TEAL} !important; color: white !important; }}
    .new-student-box {{
        background: #fff8e1; border: 2px dashed {AMBER};
        border-radius: 8px; padding: 14px; margin-top: 8px;
    }}
    /* ── Persistent section toggle ── */
    .sec-header {{
        display: flex; align-items: center; justify-content: space-between;
        background: white; border: 1px solid #d0e0e0;
        border-radius: 8px; padding: 10px 16px; margin: 6px 0;
        cursor: pointer; user-select: none;
    }}
    .sec-header:hover {{ background: #f0f8f8; }}
    .sec-left {{ display: flex; align-items: center; gap: 10px; font-weight: 600; font-size: 0.95rem; color: #1a1a1a; }}
    .sec-right {{ display: flex; align-items: center; gap: 10px; }}
    .sec-pill {{
        padding: 3px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 700;
    }}
    .sec-pill.high {{ background: #fde8e8; color: #c62828; }}
    .sec-pill.med  {{ background: #fff3e0; color: #e65100; }}
    .sec-pill.low  {{ background: #e8f5e9; color: #2e7d32; }}
    .sec-body {{
        background: white; border: 1px solid #d0e0e0; border-top: none;
        border-radius: 0 0 8px 8px; padding: 14px 16px; margin-top: -8px; margin-bottom: 6px;
    }}
    div[data-testid="stButton"] button[kind="secondary"] {{
        background: transparent; border: none; padding: 0;
        font-size: 0.9rem; color: #555; text-align: left; width: 100%;
    }}
</style>
""", unsafe_allow_html=True)

# ── Supabase ───────────────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = get_supabase()

# ── Section definitions ────────────────────────────────────────────────────────
SECTIONS = {
    "Body Awareness (Interoception)": {
        "icon": "🫀",
        "items": [
            "Able to name own emotions",
            "Able to recognise own emotions",
            "Knows when thirsty",
            "Knows when hungry",
            "Knows when they need to go to the toilet",
            "Able to say where hurts (accurately) when injured",
            "Knows when they feel unwell",
            "Knows when getting upset",
            "Gets distressed easily or frequently",
            "Knows when becoming anxious",
            "Gets anxious easily or frequently",
            "Knows when getting frustrated",
            "Knows when becoming angry",
            "Gets frustrated/angry easily",
            "Seems to react to the emotions of others/places",
        ],
    },
    "Visual": {
        "icon": "👁️",
        "items": [
            "Does not recognise familiar people in unfamiliar clothes or contexts",
            "Dislikes bright lights",
            "Dislikes fluorescent lights",
            "Avoids bright light",
            "Attracted to lights",
            "Attracted to shiny objects and bright colours",
            "Attracted to patterns and visual textures",
            "Attracted to darkness",
        ],
    },
    "Sense of Body in Space": {
        "icon": "🗺️",
        "items": [
            "Does not seem to know where body is in space",
            "Gets lost in familiar places/routes",
            "Remembers familiar places and routes",
            "Avoids escalators/travellators",
            "Dislikes crowds or being close to others",
            "Difficulties catching a ball",
            "Difficulties kicking a ball",
            "Appears to not see certain colours",
            "Walks into doors/people/objects",
            "Prefers to sit at the front of a group",
            "Prefers to sit at back of group",
        ],
    },
    "Auditory": {
        "icon": "👂",
        "items": [
            "Aversion to certain sounds",
            "Seeks or creates certain sounds",
            "Can hear sounds which others do not hear",
            "Bangs objects and doors",
            "Mumbles/talks/makes vocalisations to self constantly",
            "Changes vocalisations in reaction to environmental noises",
            "Changes vocalisations in reaction to emotional state",
        ],
    },
    "Auditory Processing": {
        "icon": "🔊",
        "items": [
            "Only seems to hear the first words of a sentence",
            "Can follow complex or multi-step instructions",
            "Can follow simple one step instructions",
            "Finds it easier to listen when not looking at person",
            "Echolalic (repeats phrases)",
        ],
    },
    "Smell": {
        "icon": "👃",
        "items": [
            "Avoids/dislikes certain everyday smells",
            "Attracted to certain smells",
        ],
    },
    "Touch and Textures": {
        "icon": "🤚",
        "items": [
            "Does not like shaking hands or being hugged",
            "Seeks/uses light touch",
            "Seeks/uses firm touch/deep pressure (incl. hitting)",
            "Aversion to certain fabrics/textures",
            "Attracted to certain fabrics/textures",
            "Very sensitive to pain and temperature",
            "Does not indicate sensitivity to pain or temperature",
            "Attracted to mouthing/chewing certain textures/things",
            "Avoids particular textures of food & drink",
            "Avoids particular colours/smells of food & drink",
            "Preference for food to not touch other food on plate",
        ],
    },
    "Kinaesthetic": {
        "icon": "🏃",
        "items": [
            "Tries to avoid using fine motor skills",
            "Enjoys using fine motor skills",
            "Difficulties with fine motor skills",
            "Tries to avoid running and/or climbing",
            "Enjoys running and/or climbing",
            "Difficulty running and/or climbing",
            "Tries to avoid riding a bike",
            "Enjoys riding a bike",
            "Poor balance",
            "Has extremely good balance",
            "Enjoys/seeks out swings",
            "Enjoys/seeks out trampolines",
            "Enjoys/seeks out slides",
            "Flaps hands when happy",
            "Flaps hands when anxious",
        ],
    },
}

# ── Helpers ────────────────────────────────────────────────────────────────────
def priority_info(pct):
    if pct >= 60:
        return "HIGH PRIORITY", "high", "🔴"
    elif pct >= 30:
        return "MEDIUM PRIORITY", "med", "🟡"
    return "LOW PRIORITY", "low", "🟢"

def calc_priorities(responses):
    results = {}
    for sec, meta in SECTIONS.items():
        items = meta["items"]
        sec_resp = responses.get(sec, {})
        checked = sum(1 for it in items if sec_resp.get(it, False))
        pct = round((checked / len(items)) * 100, 1) if items else 0
        label, css, emoji = priority_info(pct)
        results[sec] = {"priority": label, "css": css, "emoji": emoji,
                        "checked": checked, "total": len(items), "pct": pct}
    return results

def priority_card(section_name, info, icon=""):
    return f"""
    <div class="priority-card {info['css']}">
        <div class="label">{icon} {section_name}</div>
        <div class="pval">{info['emoji']} {info['priority']}</div>
        <div class="sub">{info['checked']} / {info['total']} items ({info['pct']}%)</div>
    </div>"""

@st.cache_data(ttl=60)
def load_students():
    """Load all active students from the shared students table."""
    try:
        res = supabase.table("students").select("id,name,edid,program,grade,dob") \
            .eq("archived", False).order("name").execute()
        return res.data or []
    except Exception as e:
        st.error(f"Could not load students: {e}")
        return []

def load_all_overviews():
    try:
        res = supabase.table("sensory_overviews") \
            .select("*, students(name,edid,program)") \
            .order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        st.error(f"Could not load overviews: {e}")
        return []

def create_student_inline(name, edid, program, grade, dob):
    """Create a new student in the shared students table."""
    try:
        # grade is integer in DB — convert safely
        try:
            grade_int = int(grade) if grade else None
        except ValueError:
            grade_int = None
        payload = {
            "name":            name.strip(),
            "edid":            edid.strip(),
            "program":         program,
            "grade":           grade_int,
            "dob":             str(dob),
            "placement_start": str(date.today()),
            "archived":        False,
        }
        res = supabase.table("students").insert(payload).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        st.error(f"Could not create student: {e}")
        return None

# ── Session state ──────────────────────────────────────────────────────────────
if "responses" not in st.session_state:
    st.session_state.responses = {sec: {it: False for it in m["items"]} for sec, m in SECTIONS.items()}
if "saved_ok" not in st.session_state:
    st.session_state.saved_ok = False
if "selected_student_id" not in st.session_state:
    st.session_state.selected_student_id = None
if "preselect_student_id" not in st.session_state:
    st.session_state.preselect_student_id = None
if "section_open" not in st.session_state:
    st.session_state.section_open = {sec: False for sec in SECTIONS}

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("<h1>🧠 Sensory Overview</h1>", unsafe_allow_html=True)

# Check for ?student_id= query param (launched from behaviour app)
params = st.query_params
deep_link_id = params.get("student_id", None)
if deep_link_id and not st.session_state.preselect_student_id:
    st.session_state.preselect_student_id = deep_link_id

tab_new, tab_past = st.tabs(["📝  New Overview", "📋  Past Overviews"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — NEW OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab_new:

    if st.session_state.saved_ok:
        st.success("✅ Overview saved successfully!")
        if st.button("Start another overview"):
            st.session_state.responses = {sec: {it: False for it in m["items"]} for sec, m in SECTIONS.items()}
            st.session_state.saved_ok = False
            st.session_state.selected_student_id = None
            st.rerun()

    # ── Student selection ──────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("#### 👤 Student")

        students = load_students()
        student_options = {s["id"]: f"{s['name']} ({s.get('program','?')} · {s.get('edid','—')})" for s in students}

        # Determine default index for deep-link
        default_idx = 0
        all_ids = ["— Select a student —"] + list(student_options.keys())
        if st.session_state.preselect_student_id and st.session_state.preselect_student_id in student_options:
            default_idx = all_ids.index(st.session_state.preselect_student_id)

        selected_raw = st.selectbox(
            "Select existing student",
            options=all_ids,
            index=default_idx,
            format_func=lambda x: student_options.get(x, x),
        )

        selected_student_id   = selected_raw if selected_raw != "— Select a student —" else None
        selected_student_data = next((s for s in students if s["id"] == selected_student_id), None)

        if selected_student_data:
            st.markdown(
                f'<div class="student-badge">✅ {selected_student_data["name"]} '
                f'· {selected_student_data.get("program","?")} '
                f'· {selected_student_data.get("grade","?")}</div>',
                unsafe_allow_html=True,
            )

        # ── Add new student inline ─────────────────────────────────────────────
        with st.expander("➕ Student not in the list? Add them here"):
            st.markdown('<div class="new-student-box">', unsafe_allow_html=True)
            nc1, nc2 = st.columns(2)
            with nc1:
                new_name    = st.text_input("Full name *")
                new_edid    = st.text_input("EDID *")
                new_program = st.selectbox("Program *", ["JP", "PY", "SY"])
            with nc2:
                new_grade   = st.number_input("Year level", min_value=0, max_value=12, step=1, value=0)
                new_dob     = st.date_input("Date of birth *", value=None)

            if st.button("Create student & use for this overview", type="primary"):
                if not new_name or not new_edid or not new_dob:
                    st.error("Name, EDID and Date of Birth are required.")
                else:
                    created = create_student_inline(new_name, new_edid, new_program, new_grade, new_dob)
                    if created:
                        st.success(f"✅ {new_name} added to the students database.")
                        load_students.clear()
                        st.session_state.selected_student_id = created["id"]
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Other overview fields ──────────────────────────────────────────────
        oc1, oc2, oc3 = st.columns(3)
        with oc1:
            overview_date = st.date_input("Overview Date", value=date.today())
        with oc2:
            review_date   = st.date_input("Review Date")
        with oc3:
            completed_by  = st.text_input("Completed by", placeholder="Staff name")

    # ── Existing overviews for this student ────────────────────────────────────
    if selected_student_id:
        existing = supabase.table("sensory_overviews") \
            .select("overview_date,completed_by,priority_results") \
            .eq("student_id", selected_student_id) \
            .order("overview_date", desc=True).limit(1).execute()
        if existing.data:
            prev = existing.data[0]
            with st.expander(f"ℹ️ Previous overview exists — {prev['overview_date']} (by {prev['completed_by']})", expanded=False):
                try:
                    pr = json.loads(prev["priority_results"]) if isinstance(prev["priority_results"], str) else prev["priority_results"]
                    cols = st.columns(4)
                    for idx, (sec, info) in enumerate(pr.items()):
                        icon = SECTIONS.get(sec, {}).get("icon", "")
                        _, css, emoji = priority_info(info.get("pct", 0))
                        info["css"] = css
                        info["emoji"] = emoji
                        with cols[idx % 4]:
                            st.markdown(priority_card(sec, info, icon), unsafe_allow_html=True)
                except Exception:
                    pass

    st.markdown("---")

    # ── Checklist sections ─────────────────────────────────────────────────────
    st.markdown("#### Checklist — tick all items that apply")

    # Expand / collapse all controls
    ctrl1, ctrl2 = st.columns([1, 1])
    with ctrl1:
        if st.button("⬇️  Expand all sections", use_container_width=True):
            for sec in SECTIONS:
                st.session_state.section_open[sec] = True
            st.rerun()
    with ctrl2:
        if st.button("⬆️  Collapse all sections", use_container_width=True):
            for sec in SECTIONS:
                st.session_state.section_open[sec] = False
            st.rerun()

    for sec_name, meta in SECTIONS.items():
        icon  = meta["icon"]
        items = meta["items"]
        sec_resp      = st.session_state.responses.get(sec_name, {})
        checked_count = sum(1 for it in items if sec_resp.get(it, False))
        pct           = round((checked_count / len(items)) * 100) if items else 0
        _, css, emoji = priority_info(pct)
        is_open       = st.session_state.section_open.get(sec_name, False)
        chevron       = "🔽" if is_open else "▶️"

        # Header row — clicking the button toggles open/closed
        hdr_col, btn_col = st.columns([8, 1])
        with hdr_col:
            st.markdown(
                f"""<div class="sec-header">
                    <div class="sec-left">{icon} <span>{sec_name}</span></div>
                    <div class="sec-right">
                        <span class="sec-pill {css}">{emoji} {checked_count}/{len(items)}</span>
                        <span style="color:#888;font-size:0.85rem;">{chevron}</span>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )
        with btn_col:
            # Invisible toggle button aligned over the header
            if st.button(
                chevron,
                key=f"toggle_{sec_name}",
                help=f"{'Collapse' if is_open else 'Expand'} {sec_name}",
                use_container_width=True,
            ):
                st.session_state.section_open[sec_name] = not is_open
                st.rerun()

        # Body — only rendered when open, state persists through checkbox reruns
        if is_open:
            with st.container(border=True):
                cols = st.columns(2)
                for i, item in enumerate(items):
                    with cols[i % 2]:
                        val = st.checkbox(
                            item,
                            value=st.session_state.responses[sec_name].get(item, False),
                            key=f"chk_{sec_name}_{item}",
                        )
                        st.session_state.responses[sec_name][item] = val

    st.markdown("---")

    # ── Results summary ────────────────────────────────────────────────────────
    st.markdown("#### Results Summary")
    priorities = calc_priorities(st.session_state.responses)
    cols = st.columns(4)
    for idx, (sec, info) in enumerate(priorities.items()):
        icon = SECTIONS[sec]["icon"]
        with cols[idx % 4]:
            st.markdown(priority_card(sec, info, icon), unsafe_allow_html=True)

    st.markdown("---")

    # ── Save ───────────────────────────────────────────────────────────────────
    btn_col, clr_col = st.columns([3, 1])
    with btn_col:
        if st.button("💾  Save Overview", type="primary", use_container_width=True):
            if not selected_student_id:
                st.error("Please select a student before saving.")
            else:
                store_priorities = {
                    sec: {"priority": v["priority"], "checked": v["checked"],
                          "total": v["total"], "pct": v["pct"]}
                    for sec, v in priorities.items()
                }
                payload = {
                    "student_id":       selected_student_id,
                    "student_name":     selected_student_data["name"] if selected_student_data else "",
                    "overview_date":    str(overview_date),
                    "review_date":      str(review_date),
                    "completed_by":     completed_by.strip(),
                    "responses":        json.dumps(st.session_state.responses),
                    "priority_results": json.dumps(store_priorities),
                }
                try:
                    supabase.table("sensory_overviews").insert(payload).execute()
                    st.session_state.saved_ok = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Save failed: {e}")

    with clr_col:
        if st.button("🗑️  Clear", use_container_width=True):
            st.session_state.responses = {sec: {it: False for it in m["items"]} for sec, m in SECTIONS.items()}
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PAST OVERVIEWS
# ══════════════════════════════════════════════════════════════════════════════
with tab_past:
    st.markdown("#### Past Sensory Overviews")
    records = load_all_overviews()

    if not records:
        st.info("No overviews saved yet.")
    else:
        f1, f2 = st.columns([2, 2])
        with f1:
            student_names = sorted(set(
                (r.get("students") or {}).get("name") or r.get("student_name", "Unknown")
                for r in records
            ))
            sel_student = st.selectbox("Filter by student", ["— All —"] + student_names)
        with f2:
            search = st.text_input("Search by staff / date", placeholder="e.g. Candice or 2026-03")

        filtered = records
        if sel_student != "— All —":
            filtered = [r for r in filtered if
                        ((r.get("students") or {}).get("name") or r.get("student_name")) == sel_student]
        if search:
            s = search.lower()
            filtered = [r for r in filtered if
                        s in (r.get("completed_by") or "").lower()
                        or s in (r.get("overview_date") or "").lower()]

        st.caption(f"Showing {len(filtered)} of {len(records)} records")

        for rec in filtered:
            sdata     = rec.get("students") or {}
            sname     = sdata.get("name") or rec.get("student_name", "Unknown")
            program   = sdata.get("program", "")
            ov_date   = rec.get("overview_date", "—")
            by        = rec.get("completed_by", "—")
            rev_date  = rec.get("review_date", "—")

            with st.expander(
                f"**{sname}** {f'· {program}' if program else ''} · {ov_date} · {by}",
                expanded=False
            ):
                st.markdown(f"**Review date:** {rev_date}")

                try:
                    pr = rec["priority_results"]
                    if isinstance(pr, str):
                        pr = json.loads(pr)
                except Exception:
                    pr = {}

                if pr:
                    p_cols = st.columns(4)
                    for idx, (sec, info) in enumerate(pr.items()):
                        icon = SECTIONS.get(sec, {}).get("icon", "")
                        _, css, emoji = priority_info(info.get("pct", 0))
                        info["css"] = css
                        info["emoji"] = emoji
                        with p_cols[idx % 4]:
                            st.markdown(priority_card(sec, info, icon), unsafe_allow_html=True)

                if st.toggle("Show checked items", key=f"detail_{rec['id']}"):
                    try:
                        resp = rec["responses"]
                        if isinstance(resp, str):
                            resp = json.loads(resp)
                    except Exception:
                        resp = {}
                    for sec_name, items_dict in resp.items():
                        icon = SECTIONS.get(sec_name, {}).get("icon", "")
                        checked_items = [it for it, val in items_dict.items() if val]
                        if checked_items:
                            st.markdown(f"**{icon} {sec_name}**")
                            for it in checked_items:
                                st.markdown(f"&nbsp;&nbsp;&nbsp;✅ {it}")

                st.markdown("---")
                if st.button("🗑️ Delete record", key=f"del_{rec['id']}"):
                    try:
                        supabase.table("sensory_overviews").delete().eq("id", rec["id"]).execute()
                        st.success("Deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Delete failed: {e}")
