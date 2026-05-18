# ==============================================================================
# 18_Scatter_Plot_Tracker.py  -  CLC-LBU Portal
# Scatter Plot Tracker - ABA-Aligned Data Collection Tool
# ==============================================================================
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta, datetime
import json

from auth import require_auth, logout_button, get_staff_name
require_auth(app_title="CLC LBU Staff Portal", app_icon="🏫")
logout_button()

TEAL  = "#1A6B8A"
AMBER = "#D4860A"
GREEN = "#2E7D32"
RED   = "#DC2626"

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background:#f5f8fa; }
.clc-header {
    background:linear-gradient(135deg,#1A6B8A 0%,#1A6B8ABB 100%);
    color:white; padding:.85rem 1.5rem; border-radius:10px; margin-bottom:1rem;
}
.clc-header h2 { margin:0; font-size:1.25rem; }
.clc-header p  { margin:.2rem 0 0; opacity:.85; font-size:.78rem; }
.stu-card {
    background:white; border:1.5px solid #e2e8f0; border-radius:10px;
    padding:.65rem 1rem; margin-bottom:.4rem; cursor:pointer;
}
.stu-card:hover { border-color:#1A6B8A; }
.stu-active { border-color:#1A6B8A; background:#EBF4F9; }
.grid-wrap { overflow-x:auto; border:1px solid #e2e8f0; border-radius:8px; margin-bottom:.6rem; }
.sg { width:100%; border-collapse:collapse; font-size:.8rem; }
.sg th {
    background:#1A6B8A; color:white; padding:.38rem .45rem;
    text-align:center; font-size:.7rem; font-weight:600; white-space:nowrap;
}
.sg th.lh { text-align:left; min-width:50px; }
.sg th.la { text-align:left; min-width:110px; }
.sg td { padding:.25rem .35rem; border:1px solid #e2e8f0; text-align:center; vertical-align:middle; }
.sg td.tl { text-align:left; font-weight:600; color:#334155; font-size:.73rem; white-space:nowrap; background:#f8fafc; }
.sg td.al { text-align:left; color:#64748b; font-size:.7rem; background:#f8fafc; }
.c1  { background:#dbeafe; color:#1d4ed8; font-weight:700; }
.c2  { background:#fee2e2; color:#b91c1c; font-weight:700; }
.cx  { background:#f3f4f6; color:#9ca3af; font-weight:600; }
.c0  { background:#f0fdf4; color:#15803d; font-weight:600; font-size:.72rem; }
.ce  { background:white; color:#e2e8f0; font-size:.65rem; }
.kpi { background:white; border-left:4px solid #1A6B8A; border-radius:6px;
       padding:.45rem .75rem; text-align:center; margin-bottom:.4rem; }
.kpi .val { font-size:1.4rem; font-weight:700; color:#1A6B8A; }
.kpi .lbl { font-size:.67rem; color:#666; }
.kpi-a { border-color:#D4860A; }
.kpi-a .val { color:#D4860A; }
.kpi-g { border-color:#2E7D32; }
.kpi-g .val { color:#2E7D32; }
.kpi-r { border-color:#DC2626; }
.kpi-r .val { color:#DC2626; }
.ins { background:#FEF9EC; border-left:4px solid #D4860A; border-radius:6px;
       padding:.45rem .85rem; font-size:.82rem; margin-bottom:.3rem; }
.ins-ok { background:#F0FAF4; border-left:4px solid #2EA056; }
.ins-critical { background:#FEF2F2; border-left:4px solid #DC2626; }
.period-active {
    background:#f0fdf4; border:2px solid #22c55e; border-radius:10px;
    padding:.55rem 1rem; margin-bottom:.75rem; font-size:.85rem;
}
.op-def {
    background:#fefce8; border:2px solid #eab308; border-radius:8px;
    padding:.65rem .95rem; margin-bottom:.65rem; font-size:.8rem;
}
.op-def-header { font-weight:700; color:#854d0e; margin-bottom:.3rem; }
.op-def-body { color:#713f12; line-height:1.4; }
.abc-section {
    background:white; border:1.5px solid #cbd5e1; border-radius:8px;
    padding:.7rem .9rem; margin-bottom:.5rem;
}
.abc-header { 
    font-weight:700; color:#1A6B8A; font-size:.82rem; 
    margin-bottom:.4rem; border-bottom:1px solid #e2e8f0; padding-bottom:.3rem;
}
.function-tag {
    display:inline-block; padding:.2rem .5rem; border-radius:4px;
    font-size:.7rem; font-weight:600; margin-right:.3rem; margin-bottom:.2rem;
}
.f-attention { background:#dbeafe; color:#1d4ed8; }
.f-escape { background:#fef3c7; color:#b45309; }
.f-tangible { background:#dcfce7; color:#15803d; }
.f-sensory { background:#f3e8ff; color:#6b21a8; }
.f-unknown { background:#f1f5f9; color:#64748b; }
.ioa-section {
    background:#f0f9ff; border-left:4px solid #0284c7; border-radius:6px;
    padding:.5rem .8rem; font-size:.75rem; margin-bottom:.5rem;
}
</style>
""", unsafe_allow_html=True)

DEFAULT_SCHEDULE = [
    {"time":"9:00",  "activity":""},
    {"time":"9:15",  "activity":""},
    {"time":"9:20",  "activity":""},
    {"time":"10:00", "activity":""},
    {"time":"10:05", "activity":""},
    {"time":"10:20", "activity":""},
    {"time":"10:30", "activity":""},
    {"time":"11:00", "activity":""},
    {"time":"11:30", "activity":""},
    {"time":"11:40", "activity":""},
    {"time":"12:30", "activity":""},
    {"time":"12:50", "activity":""},
    {"time":"13:00", "activity":""},
    {"time":"13:30", "activity":""},
    {"time":"13:45", "activity":""},
    {"time":"14:30", "activity":""},
]
DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday"]


# -----------------------------------------------------------------------------─ Supabase ──────────────────────────────────────────────────────────────────
def get_sb():
    try:
        from supabase import create_client
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception:
        return None


# ==============================================================================
# ABA-ALIGNED DATA STRUCTURES
# ==============================================================================

BEHAVIOUR_CATEGORIES = [
    "Physical - peer directed",
    "Physical - adult directed",
    "Self-injurious",
    "Property / environment",
    "Elopement / movement",
    "Verbal",
    "Refusal / non-compliance",
    "Dysregulation / other",
]

# Function-based analysis categories (aligned with ABA)
BEHAVIOUR_FUNCTIONS = {
    "attention": {
        "label": "Attention",
        "desc": "Behaviour maintained by access to attention (peer or adult)",
        "examples": ["Calling out", "Interrupting", "Physical contact to gain attention"]
    },
    "escape": {
        "label": "Escape/Avoidance",
        "desc": "Behaviour maintained by escape from or avoidance of tasks/demands",
        "examples": ["Task refusal", "Elopement during instruction", "Disruptive behaviour during work"]
    },
    "tangible": {
        "label": "Tangible/Access",
        "desc": "Behaviour maintained by access to preferred items or activities",
        "examples": ["Grabbing items", "Refusal when item denied", "Escalation to access preferred activity"]
    },
    "sensory": {
        "label": "Automatic/Sensory",
        "desc": "Behaviour maintained by internal/automatic reinforcement",
        "examples": ["Self-stimulation", "Repetitive behaviours", "Behaviour when alone"]
    },
    "unknown": {
        "label": "Unknown/Multiple",
        "desc": "Function not yet determined or behaviour serves multiple functions",
        "examples": []
    }
}

# ABC Recording - Antecedents
ANTECEDENTS = {
    "Demand/Task": [
        "Instruction given",
        "Task presented",
        "Transition requested",
        "Task difficulty increase",
        "Multi-step direction",
    ],
    "Social": [
        "Peer interaction",
        "Adult correction",
        "Denied request",
        "Peer conflict",
        "Group activity",
    ],
    "Environmental": [
        "Loud noise",
        "Crowded space",
        "Change in routine",
        "Preferred item removed",
        "Sensory trigger",
    ],
    "Internal State": [
        "Dysregulated arrival",
        "Post-break",
        "Hungry/tired",
        "Medication change",
        "Illness suspected",
    ],
}

# ABC Recording - Consequences
CONSEQUENCES = {
    "Attention Given": [
        "Verbal redirect",
        "Physical prompt",
        "Staff discussion with student",
        "Peer response",
        "Sent to leadership",
    ],
    "Escape Provided": [
        "Task removed",
        "Break given",
        "Moved to different area",
        "Time out from instruction",
        "Left activity",
    ],
    "Tangible Delivered": [
        "Access to preferred item",
        "Access to preferred activity",
        "Sensory item provided",
        "Technology access",
    ],
    "Planned Consequence": [
        "Natural consequence",
        "Logical consequence",
        "Restorative conversation",
        "No response (planned ignoring)",
        "Differential reinforcement",
    ],
}

# Measurement precision
FREQUENCY_MEASURES = {
    "0": "Not observed",
    "1": "1 instance",
    "2": "2 instances",
    "3": "3 instances",
    "4": "4 instances",
    "5+": "5 or more instances",
    "X": "Could not observe",
}

# Setting/grouping factors
GROUPINGS = {
    "i":   "Independent",
    "1:1": "One-to-one",
    "sg":  "Small group (2-5)",
    "lg":  "Large group (6+)",
    "U":   "Unstructured",
    "P":   "Peer only",
}

SETTINGS = ["Classroom","Kitchen","Yard","Playground","Spill-out","Transition","Other"]

# Intervention fidelity tracking
INTERVENTIONS_IN_PLACE = [
    "Visual schedule",
    "Choice board",
    "First-then board",
    "Token economy",
    "Self-monitoring",
    "Break card",
    "Sensory supports",
    "Modified task",
    "Peer support",
    "1:1 support",
    "Pre-correction",
    "Behavioural contract",
    "Other (specify)",
]


# ==============================================================================═════════════════════════════════════════════════════════════════════════════
# OPERATIONAL DEFINITIONS - CORE ABA REQUIREMENT
# ==============================================================================═════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=120)
def load_behaviour_bank():
    """Load all behaviours with operational definitions from Supabase bank."""
    sb = get_sb()
    if not sb: return {}
    try:
        res = sb.table("scatter_behaviour_bank").select("*").order("category").order("description").execute()
        bank = {}
        for row in (res.data or []):
            cat = row["category"]
            if cat not in bank:
                bank[cat] = []
            bank[cat].append({
                "id": row["id"], 
                "description": row["description"],
                "operational_definition": row.get("operational_definition", ""),
                "examples": row.get("examples", ""),
                "non_examples": row.get("non_examples", ""),
                "measurement_type": row.get("measurement_type", "frequency"),
                "hypothesized_function": row.get("hypothesized_function", "unknown"),
                "is_custom": row.get("is_custom", False)
            })
        return bank
    except Exception:
        return {}


def add_custom_behaviour(category, description, operational_definition="", examples="", non_examples=""):
    """Add custom behaviour with operational definition."""
    sb = get_sb()
    if not sb: return False
    try:
        sb.table("scatter_behaviour_bank").insert({
            "category": category, 
            "description": description, 
            "operational_definition": operational_definition,
            "examples": examples,
            "non_examples": non_examples,
            "measurement_type": "frequency",
            "is_custom": True
        }).execute()
        load_behaviour_bank.clear()
        return True
    except Exception as e:
        st.error("Could not save: " + str(e))
        return False


def update_behaviour_definition(behaviour_id, operational_definition, examples="", non_examples="", hypothesized_function="unknown"):
    """Update operational definition for existing behaviour."""
    sb = get_sb()
    if not sb: return False
    try:
        sb.table("scatter_behaviour_bank").update({
            "operational_definition": operational_definition,
            "examples": examples,
            "non_examples": non_examples,
            "hypothesized_function": hypothesized_function,
        }).eq("id", behaviour_id).execute()
        load_behaviour_bank.clear()
        return True
    except Exception as e:
        st.error("Could not update: " + str(e))
        return False


def delete_behaviour(beh_id):
    sb = get_sb()
    if not sb: return False
    try:
        sb.table("scatter_behaviour_bank").delete().eq("id", beh_id).eq("is_custom", True).execute()
        load_behaviour_bank.clear()
        return True
    except Exception:
        return False


# ==============================================================================═════════════════════════════════════════════════════════════════════════════
# STUDENT & PERIOD MANAGEMENT
# ==============================================================================═════════════════════════════════════════════════════════════════════════════

def init_state():
    ss = st.session_state
    if "spt_student_name" not in ss:  ss.spt_student_name = ""
    if "spt_period_id" not in ss:     ss.spt_period_id = None
    if "spt_mode" not in ss:          ss.spt_mode = "collect"
    if "spt_prog_type" not in ss:     ss.spt_prog_type = ""
    if "spt_behs" not in ss:          ss.spt_behs = []
    if "spt_schedule" not in ss:      ss.spt_schedule = DEFAULT_SCHEDULE.copy()
    if "spt_view_defs" not in ss:     ss.spt_view_defs = False
    if "spt_abc_enabled" not in ss:   ss.spt_abc_enabled = False
    if "spt_ioa_mode" not in ss:      ss.spt_ioa_mode = False
    if "spt_secondary_observer" not in ss: ss.spt_secondary_observer = ""

init_state()
ss = st.session_state

st.markdown("""
<div class='clc-header'>
<h2>📊 Scatter Plot Tracker - ABA Edition</h2>
<p>Evidence-based behaviour data collection with operational definitions, ABC analysis, and function-based tracking</p>
</div>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------─ LOAD STUDENTS ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def load_students():
    sb = get_sb()
    if not sb: return []
    try:
        res = sb.table("scatter_students").select("*").order("student_name").execute()
        return res.data or []
    except Exception:
        return []

students = load_students()

if not students:
    st.info("⚠️ No students configured. Add students via Portal Admin.")
    st.stop()


# ==============================================================================═════════════════════════════════════════════════════════════════════════════
# MAIN WORKFLOW
# ==============================================================================═════════════════════════════════════════════════════════════════════════════

mode_choice = st.radio(
    "Choose mode:",
    ["📝 Data Collection", "📊 Analysis & Reports", "⚙️ Manage Behaviours & Definitions"],
    horizontal=True,
    label_visibility="collapsed"
)

if "Manage Behaviours" in mode_choice:
    ss.spt_mode = "manage"
elif "Analysis" in mode_choice:
    ss.spt_mode = "analyse"
else:
    ss.spt_mode = "collect"


# ==============================================================================═════════════════════════════════════════════════════════════════════════════
# MODE: MANAGE BEHAVIOURS & OPERATIONAL DEFINITIONS
# ==============================================================================═════════════════════════════════════════════════════════════════════════════

if ss.spt_mode == "manage":
    st.markdown("### ⚙️ Behaviour Bank - Operational Definitions")
    st.markdown("""
    <div class='ins'>
    <b>ABA Standard:</b> Every behaviour must have a clear operational definition that is:
    <ul style='margin:.3rem 0;padding-left:1.2rem;'>
    <li><b>Observable:</b> Can be seen or heard by an independent observer</li>
    <li><b>Measurable:</b> Can be counted, timed, or rated</li>
    <li><b>Clear:</b> Two observers can independently identify the same behaviour</li>
    <li><b>Complete:</b> Includes examples and non-examples to prevent ambiguity</li>
    </ul>
    This ensures inter-observer reliability and treatment validity.
    </div>
    """, unsafe_allow_html=True)
    
    bank = load_behaviour_bank()
    
    tab1, tab2 = st.tabs(["📋 View/Edit Definitions", "➕ Add New Behaviour"])
    
    with tab1:
        if not bank:
            st.info("No behaviours in bank yet.")
        else:
            for category in BEHAVIOUR_CATEGORIES:
                if category in bank and bank[category]:
                    st.markdown(f"#### {category}")
                    for beh in bank[category]:
                        with st.expander(f"**{beh['description']}**" + (" 🔧" if beh['is_custom'] else "")):
                            # Display current definition
                            op_def = beh.get('operational_definition', '')
                            examples = beh.get('examples', '')
                            non_examples = beh.get('non_examples', '')
                            func = beh.get('hypothesized_function', 'unknown')
                            
                            if op_def:
                                st.markdown(f"<div class='op-def'><div class='op-def-header'>Operational Definition:</div><div class='op-def-body'>{op_def}</div></div>", unsafe_allow_html=True)
                            else:
                                st.warning("⚠️ No operational definition set - required for ABA compliance")
                            
                            if examples:
                                st.markdown(f"**Examples:** {examples}")
                            if non_examples:
                                st.markdown(f"**Non-examples:** {non_examples}")
                            
                            st.markdown(f"**Hypothesized Function:** {BEHAVIOUR_FUNCTIONS[func]['label']}")
                            
                            # Edit section
                            st.markdown("---")
                            st.markdown("**Edit Definition:**")
                            new_op_def = st.text_area(
                                "Operational Definition",
                                value=op_def,
                                key=f"opdef_{beh['id']}",
                                help="Clear, observable, measurable description of the behaviour",
                                height=80
                            )
                            new_examples = st.text_input(
                                "Examples (comma-separated)",
                                value=examples,
                                key=f"ex_{beh['id']}"
                            )
                            new_non_examples = st.text_input(
                                "Non-examples (comma-separated)",
                                value=non_examples,
                                key=f"nex_{beh['id']}"
                            )
                            new_func = st.selectbox(
                                "Hypothesized Function",
                                options=list(BEHAVIOUR_FUNCTIONS.keys()),
                                format_func=lambda x: BEHAVIOUR_FUNCTIONS[x]['label'],
                                index=list(BEHAVIOUR_FUNCTIONS.keys()).index(func),
                                key=f"func_{beh['id']}"
                            )
                            
                            col1, col2 = st.columns([1, 1])
                            with col1:
                                if st.button("💾 Save Definition", key=f"save_{beh['id']}", use_container_width=True):
                                    if update_behaviour_definition(beh['id'], new_op_def, new_examples, new_non_examples, new_func):
                                        st.success("✅ Definition updated")
                                        st.rerun()
                            with col2:
                                if beh['is_custom']:
                                    if st.button("🗑️ Delete", key=f"del_{beh['id']}", use_container_width=True):
                                        if delete_behaviour(beh['id']):
                                            st.success("✅ Behaviour deleted")
                                            st.rerun()
    
    with tab2:
        st.markdown("**Add Custom Behaviour to Bank:**")
        new_cat = st.selectbox("Category", BEHAVIOUR_CATEGORIES, key="new_cat")
        new_desc = st.text_input("Behaviour Label", key="new_desc", help="Brief name/label for the behaviour")
        new_opdef = st.text_area(
            "Operational Definition (Required)", 
            key="new_opdef",
            help="Observable, measurable description",
            height=100
        )
        new_ex = st.text_input("Examples (comma-separated)", key="new_ex")
        new_nex = st.text_input("Non-examples (comma-separated)", key="new_nex")
        new_func_add = st.selectbox(
            "Hypothesized Function",
            options=list(BEHAVIOUR_FUNCTIONS.keys()),
            format_func=lambda x: BEHAVIOUR_FUNCTIONS[x]['label'],
            key="new_func"
        )
        
        if st.button("➕ Add Behaviour", type="primary", use_container_width=True):
            if not new_desc.strip():
                st.error("Behaviour label required")
            elif not new_opdef.strip():
                st.error("Operational definition required for ABA compliance")
            else:
                if add_custom_behaviour(new_cat, new_desc.strip(), new_opdef.strip(), new_ex.strip(), new_nex.strip()):
                    st.success("✅ Behaviour added to bank")
                    st.rerun()
    
    st.stop()


# ==============================================================================═════════════════════════════════════════════════════════════════════════════
# STUDENT & PERIOD SELECTION (FOR COLLECT & ANALYSE MODES)
# ==============================================================================═════════════════════════════════════════════════════════════════════════════

st.markdown("### 1. Select Student")

# Student cards
for stu in students:
    active = (ss.spt_student_name == stu["student_name"])
    card_class = "stu-card stu-active" if active else "stu-card"
    st.markdown(
        f"<div class='{card_class}'><b>{stu['student_name']}</b> - {stu.get('program_type', '-')}</div>",
        unsafe_allow_html=True
    )
    if st.button(f"Select {stu['student_name']}", key=f"sel_{stu['id']}", use_container_width=True):
        ss.spt_student_name = stu["student_name"]
        ss.spt_prog_type = stu.get("program_type", "")
        ss.spt_period_id = None
        ss.spt_behs = []
        st.rerun()

if not ss.spt_student_name:
    st.info("👆 Select a student to continue")
    st.stop()

student_name = ss.spt_student_name

st.markdown(f"**Selected:** {student_name}")
st.markdown("---")

# -----------------------------------------------------------------------------─ LOAD PERIODS ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def load_periods(student_name):
    sb = get_sb()
    if not sb: return []
    try:
        res = (sb.table("scatter_tracking_periods")
               .select("*")
               .eq("student_name", student_name)
               .order("start_date", desc=True)
               .execute())
        return res.data or []
    except Exception:
        return []

periods = load_periods(student_name)

st.markdown("### 2. Select Tracking Period")

if not periods:
    st.info(f"No tracking periods configured for {student_name}. Create one via Portal Admin.")
    st.stop()

for p in periods:
    active = (ss.spt_period_id == p["id"])
    card_class = "stu-card stu-active" if active else "stu-card"
    label = p.get("label", "Untitled")
    sd = pd.to_datetime(p["start_date"]).strftime("%-d %b %Y")
    ed = pd.to_datetime(p["end_date"]).strftime("%-d %b %Y") if p.get("end_date") else "ongoing"
    st.markdown(
        f"<div class='{card_class}'><b>{label}</b> - {sd} – {ed}</div>",
        unsafe_allow_html=True
    )
    if st.button(f"Select {label}", key=f"per_{p['id']}", use_container_width=True):
        ss.spt_period_id = p["id"]
        # Load behaviours and schedule for this period
        ss.spt_behs = json.loads(p.get("target_behaviours") or "[]")
        ss.spt_schedule = json.loads(p.get("schedule") or json.dumps(DEFAULT_SCHEDULE))
        st.rerun()

if not ss.spt_period_id:
    st.info("👆 Select a tracking period")
    st.stop()

# Display active period
for p in periods:
    if p["id"] == ss.spt_period_id:
        label = p.get("label", "Untitled")
        sd = pd.to_datetime(p["start_date"]).strftime("%-d %b %Y")
        ed = pd.to_datetime(p["end_date"]).strftime("%-d %b %Y") if p.get("end_date") else "ongoing"
        st.markdown(f"<div class='period-active'>📅 <b>Active Period:</b> {label} ({sd} – {ed})</div>", unsafe_allow_html=True)
        break

behaviours = ss.spt_behs
schedule = ss.spt_schedule

if not behaviours:
    st.warning(f"⚠️ No target behaviours defined for this period. Configure via Portal Admin.")
    st.stop()

st.markdown("---")


# ==============================================================================═════════════════════════════════════════════════════════════════════════════
# MODE: DATA COLLECTION WITH ABA FRAMEWORK
# ==============================================================================═════════════════════════════════════════════════════════════════════════════

if ss.spt_mode == "collect":
    st.markdown("### 3. Operational Definitions - Review Before Recording")
    
    st.markdown("""
    <div class='ins-critical'>
    <b>⚠️ ABA Requirement:</b> Review operational definitions before each data collection session.
    This ensures consistency and inter-observer reliability across sessions and staff.
    </div>
    """, unsafe_allow_html=True)
    
    # Load behaviour bank to get operational definitions
    bank = load_behaviour_bank()
    
    # Display operational definitions for target behaviours
    for idx, beh_label in enumerate(behaviours):
        # Find this behaviour in the bank
        op_def_found = False
        for cat in bank.values():
            for beh_data in cat:
                if beh_data['description'] == beh_label:
                    op_def = beh_data.get('operational_definition', '')
                    examples = beh_data.get('examples', '')
                    non_examples = beh_data.get('non_examples', '')
                    func = beh_data.get('hypothesized_function', 'unknown')
                    
                    st.markdown(f"#### Behaviour {idx+1}: {beh_label}")
                    
                    if op_def:
                        st.markdown(f"""
                        <div class='op-def'>
                            <div class='op-def-header'>Operational Definition:</div>
                            <div class='op-def-body'>{op_def}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.error(f"⚠️ No operational definition for '{beh_label}' - set definition in Manage Behaviours mode")
                    
                    if examples or non_examples or func != 'unknown':
                        with st.expander("Additional Details"):
                            if examples:
                                st.markdown(f"**Examples:** {examples}")
                            if non_examples:
                                st.markdown(f"**Non-examples:** {non_examples}")
                            if func != 'unknown':
                                func_data = BEHAVIOUR_FUNCTIONS[func]
                                st.markdown(f"**Hypothesized Function:** {func_data['label']}")
                                st.caption(func_data['desc'])
                    
                    op_def_found = True
                    break
            if op_def_found:
                break
        
        if not op_def_found:
            st.error(f"⚠️ Behaviour '{beh_label}' not found in bank - add via Manage Behaviours mode")
    
    st.markdown("---")
    
    # Data collection options
    st.markdown("### 4. Data Collection Options")
    
    col1, col2 = st.columns(2)
    with col1:
        ss.spt_abc_enabled = st.checkbox(
            "Enable ABC Recording",
            value=ss.spt_abc_enabled,
            help="Record Antecedent-Behavior-Consequence for each instance"
        )
    with col2:
        ss.spt_ioa_mode = st.checkbox(
            "Inter-Observer Reliability Mode",
            value=ss.spt_ioa_mode,
            help="Record secondary observer for IOA calculation"
        )
    
    if ss.spt_ioa_mode:
        ss.spt_secondary_observer = st.text_input(
            "Secondary Observer Name",
            value=ss.spt_secondary_observer,
            help="Name of second observer for IOA"
        )
    
    st.markdown("---")
    
    # Data collection grid
    st.markdown("### 5. Record Observations")
    
    obs_date = st.date_input("Observation Date", value=date.today(), max_value=date.today())
    day_of_week = pd.Timestamp(obs_date).strftime("%A")
    
    if day_of_week not in DAYS:
        st.warning(f"⚠️ {day_of_week} is not a school day")
        st.stop()
    
    # Intervention fidelity check
    st.markdown("**Interventions in Place Today:**")
    interventions_today = st.multiselect(
        "Select all that apply",
        INTERVENTIONS_IN_PLACE,
        key="interventions_today",
        label_visibility="collapsed"
    )
    if "Other (specify)" in interventions_today:
        other_intervention = st.text_input("Specify other intervention:", key="other_int")
        if other_intervention:
            interventions_today.append(other_intervention)
    
    # Setting events check
    setting_events = st.text_area(
        "Setting Events / Contextual Factors (if any):",
        help="E.g., arrived late, didn't eat breakfast, medication change, substitute teacher",
        key="setting_events",
        height=60
    )
    
    st.markdown("---")
    
    # Load existing observations for this date
    @st.cache_data(ttl=30, show_spinner=False)
    def load_observations(student_name, obs_date_str):
        sb = get_sb()
        if not sb: return []
        try:
            res = (sb.table("scatter_observations")
                   .select("*")
                   .eq("student_name", student_name)
                   .eq("obs_date", obs_date_str)
                   .execute())
            return res.data or []
        except Exception:
            return []
    
    existing_obs = load_observations(student_name, str(obs_date))
    
    # Build grid
    st.markdown("**Scatter Plot Grid:**")
    st.caption("Record frequency for each time slot. Use 0-5+ scale for precise measurement.")
    
    # Create lookup for existing observations
    obs_lookup = {}
    for obs in existing_obs:
        key = (obs["time_slot"], obs.get("behaviour_index", 0))
        obs_lookup[key] = obs
    
    # Display grid for each behaviour
    for beh_idx, beh_label in enumerate(behaviours):
        st.markdown(f"#### Behaviour {beh_idx+1}: {beh_label}")
        
        grid_data = []
        for slot in schedule:
            time_slot = slot["time"]
            activity = slot.get("activity", "")
            
            obs_key = (time_slot, beh_idx)
            existing = obs_lookup.get(obs_key, {})
            
            row_data = {
                "Time": time_slot,
                "Activity": activity,
                "Frequency": existing.get("value", "0"),
                "Setting": existing.get("setting", ""),
                "Grouping": existing.get("grouping", ""),
            }
            
            if ss.spt_abc_enabled:
                row_data["Antecedent"] = existing.get("antecedent", "")
                row_data["Consequence"] = existing.get("consequence", "")
                row_data["Function"] = existing.get("observed_function", "")
            
            grid_data.append(row_data)
        
        grid_df = pd.DataFrame(grid_data)
        
        # Use st.data_editor for editable grid
        edited_df = st.data_editor(
            grid_df,
            column_config={
                "Time": st.column_config.TextColumn("Time", disabled=True, width="small"),
                "Activity": st.column_config.TextColumn("Activity", disabled=True, width="medium"),
                "Frequency": st.column_config.SelectboxColumn(
                    "Frequency",
                    options=list(FREQUENCY_MEASURES.keys()),
                    required=True,
                    width="small"
                ),
                "Setting": st.column_config.SelectboxColumn("Setting", options=SETTINGS, width="medium"),
                "Grouping": st.column_config.SelectboxColumn("Grouping", options=list(GROUPINGS.keys()), width="small"),
                "Antecedent": st.column_config.TextColumn("Antecedent", width="medium") if ss.spt_abc_enabled else None,
                "Consequence": st.column_config.TextColumn("Consequence", width="medium") if ss.spt_abc_enabled else None,
                "Function": st.column_config.SelectboxColumn(
                    "Function",
                    options=list(BEHAVIOUR_FUNCTIONS.keys()),
                    width="small"
                ) if ss.spt_abc_enabled else None,
            },
            hide_index=True,
            use_container_width=True,
            key=f"grid_beh_{beh_idx}"
        )
        
        # Save button for this behaviour
        if st.button(f"💾 Save Observations for Behaviour {beh_idx+1}", key=f"save_beh_{beh_idx}", type="primary"):
            sb = get_sb()
            if not sb:
                st.error("Database connection failed")
                continue
            
            saved_count = 0
            staff = get_staff_name()
            
            for _, row in edited_df.iterrows():
                time_slot = row["Time"]
                freq = row["Frequency"]
                
                # Skip if no frequency recorded (still "0")
                if freq == "0":
                    continue
                
                obs_data = {
                    "student_name": student_name,
                    "obs_date": str(obs_date),
                    "day_of_week": day_of_week,
                    "time_slot": time_slot,
                    "activity": row["Activity"],
                    "value": freq,
                    "behaviour_index": beh_idx,
                    "behaviour_label": beh_label,
                    "target_behaviours": json.dumps(behaviours),
                    "setting": row.get("Setting", ""),
                    "grouping": row.get("Grouping", ""),
                    "created_by": staff,
                    "interventions_in_place": json.dumps(interventions_today),
                    "setting_events": setting_events,
                }
                
                if ss.spt_abc_enabled:
                    obs_data["antecedent"] = row.get("Antecedent", "")
                    obs_data["consequence"] = row.get("Consequence", "")
                    obs_data["observed_function"] = row.get("Function", "unknown")
                
                if ss.spt_ioa_mode and ss.spt_secondary_observer:
                    obs_data["secondary_observer"] = ss.spt_secondary_observer
                
                # Check if observation exists
                obs_key = (time_slot, beh_idx)
                if obs_key in obs_lookup:
                    # Update
                    try:
                        sb.table("scatter_observations")                          .update(obs_data)                          .eq("id", obs_lookup[obs_key]["id"])                          .execute()
                        saved_count += 1
                    except Exception as e:
                        st.error(f"Update failed for {time_slot}: {e}")
                else:
                    # Insert
                    try:
                        sb.table("scatter_observations").insert(obs_data).execute()
                        saved_count += 1
                    except Exception as e:
                        st.error(f"Insert failed for {time_slot}: {e}")
            
            if saved_count > 0:
                st.success(f"✅ Saved {saved_count} observations for {beh_label}")
                load_observations.clear()
                st.rerun()
            else:
                st.info("No new observations to save (all slots marked as '0')")
        
        st.markdown("---")
    
    # ABC Detail Entry (if enabled)
    if ss.spt_abc_enabled:
        st.markdown("### 6. Detailed ABC Recording (Optional)")
        st.markdown("""
        <div class='ins'>
        For incidents requiring detailed analysis, use the expanded ABC form below.
        This provides richer context than the grid alone and supports functional behaviour assessment.
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("Add Detailed ABC Record"):
            abc_time = st.time_input("Incident Time", key="abc_time")
            abc_beh = st.selectbox("Behaviour", behaviours, key="abc_beh")
            
            st.markdown("**Antecedent:**")
            abc_ant_cat = st.selectbox("Category", list(ANTECEDENTS.keys()), key="abc_ant_cat")
            abc_ant = st.selectbox("Specific Antecedent", ANTECEDENTS[abc_ant_cat], key="abc_ant")
            abc_ant_detail = st.text_area("Additional Context", key="abc_ant_detail", height=60)
            
            st.markdown("**Behaviour:**")
            abc_beh_desc = st.text_area(
                "Detailed Description (what you observed)",
                key="abc_beh_desc",
                help="Observable, specific description matching operational definition",
                height=80
            )
            abc_duration = st.number_input("Duration (seconds)", min_value=0, key="abc_dur")
            abc_intensity = st.select_slider("Intensity", options=["Low", "Medium", "High", "Severe"], key="abc_int")
            
            st.markdown("**Consequence:**")
            abc_cons_cat = st.selectbox("Category", list(CONSEQUENCES.keys()), key="abc_cons_cat")
            abc_cons = st.selectbox("Specific Consequence", CONSEQUENCES[abc_cons_cat], key="abc_cons")
            abc_cons_detail = st.text_area("Additional Context", key="abc_cons_detail", height=60)
            
            abc_function = st.selectbox(
                "Observed Function",
                options=list(BEHAVIOUR_FUNCTIONS.keys()),
                format_func=lambda x: BEHAVIOUR_FUNCTIONS[x]['label'],
                key="abc_func"
            )
            
            if st.button("💾 Save ABC Record", key="save_abc"):
                sb = get_sb()
                if not sb:
                    st.error("Database connection failed")
                else:
                    abc_data = {
                        "student_name": student_name,
                        "obs_date": str(obs_date),
                        "time": str(abc_time),
                        "behaviour_label": abc_beh,
                        "antecedent_category": abc_ant_cat,
                        "antecedent": abc_ant,
                        "antecedent_detail": abc_ant_detail,
                        "behaviour_description": abc_beh_desc,
                        "duration_seconds": abc_duration,
                        "intensity": abc_intensity,
                        "consequence_category": abc_cons_cat,
                        "consequence": abc_cons,
                        "consequence_detail": abc_cons_detail,
                        "observed_function": abc_function,
                        "created_by": get_staff_name(),
                    }
                    try:
                        sb.table("scatter_abc_records").insert(abc_data).execute()
                        st.success("✅ ABC record saved")
                    except Exception as e:
                        st.error(f"Save failed: {e}")


# ==============================================================================═════════════════════════════════════════════════════════════════════════════
# MODE: ANALYSIS & REPORTS
# ==============================================================================═════════════════════════════════════════════════════════════════════════════

elif ss.spt_mode == "analyse":
    st.markdown("### 3. Analysis Parameters")
    
    # Date range
    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input("From", value=date.today() - timedelta(days=14))
    with col2:
        date_to = st.date_input("To", value=date.today(), max_value=date.today())
    
    if date_from > date_to:
        st.error("Start date must be before end date")
        st.stop()
    
    # Load data
    @st.cache_data(ttl=60, show_spinner=False)
    def load_analysis_data(student_name, date_from_str, date_to_str):
        sb = get_sb()
        if not sb: return []
        try:
            res = (sb.table("scatter_observations")
                   .select("*")
                   .eq("student_name", student_name)
                   .gte("obs_date", date_from_str)
                   .lte("obs_date", date_to_str)
                   .order("obs_date")
                   .order("time_slot")
                   .execute())
            return res.data or []
        except Exception:
            return []
    
    data = load_analysis_data(student_name, str(date_from), str(date_to))
    
    if not data:
        st.info(f"No observations recorded for {student_name} in this date range")
        st.stop()
    
    df = pd.DataFrame(data)
    df["obs_date_dt"] = pd.to_datetime(df["obs_date"])
    
    # Convert frequency values to numeric for analysis
    def freq_to_numeric(val):
        if val == "5+": return 5
        if val == "X": return 0
        try:
            return int(val)
        except:
            return 0
    
    df["freq_numeric"] = df["value"].apply(freq_to_numeric)
    
    # Filter to only recorded incidents (exclude "0" and "X")
    incidents_df = df[df["value"].isin(["1", "2", "3", "4", "5+"])].copy()
    
    st.markdown("---")
    st.markdown("### 4. Summary Statistics")
    
    # KPIs
    total_incidents = incidents_df["freq_numeric"].sum()
    total_days = df["obs_date"].nunique()
    incidents_per_day = total_incidents / total_days if total_days > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"<div class='kpi'><div class='val'>{total_incidents}</div><div class='lbl'>Total Incidents</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='kpi kpi-a'><div class='val'>{total_days}</div><div class='lbl'>Days Observed</div></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='kpi kpi-g'><div class='val'>{incidents_per_day:.1f}</div><div class='lbl'>Avg Incidents/Day</div></div>", unsafe_allow_html=True)
    with col4:
        most_common_time = incidents_df["time_slot"].mode()[0] if not incidents_df.empty else "-"
        st.markdown(f"<div class='kpi kpi-r'><div class='val'>{most_common_time}</div><div class='lbl'>Peak Time</div></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Function-based analysis
    if "observed_function" in incidents_df.columns:
        st.markdown("### 5. Function-Based Analysis")
        
        func_counts = incidents_df["observed_function"].value_counts()
        if not func_counts.empty:
            func_fig = px.pie(
                values=func_counts.values,
                names=[BEHAVIOUR_FUNCTIONS[f]['label'] for f in func_counts.index],
                title="Behaviour Function Distribution",
                color_discrete_sequence=["#3b82f6", "#eab308", "#22c55e", "#a855f7", "#64748b"]
            )
            st.plotly_chart(func_fig, use_container_width=True)
            
            st.markdown("**Function Breakdown:**")
            for func, count in func_counts.items():
                func_data = BEHAVIOUR_FUNCTIONS[func]
                pct = (count / len(incidents_df)) * 100
                st.markdown(f"""
                <div style='padding:.4rem .6rem; background:#f8fafc; border-left:3px solid #1A6B8A; margin-bottom:.3rem; border-radius:4px;'>
                <b>{func_data['label']}</b>: {count} incidents ({pct:.0f}%)<br>
                <small style='color:#64748b;'>{func_data['desc']}</small>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
    
    # Time-based patterns
    st.markdown("### 6. Temporal Patterns")
    
    # By time slot
    time_summary = incidents_df.groupby("time_slot")["freq_numeric"].sum().reset_index()
    time_summary = time_summary.sort_values("freq_numeric", ascending=False)
    
    fig_time = px.bar(
        time_summary,
        x="time_slot",
        y="freq_numeric",
        title="Incidents by Time Slot",
        labels={"time_slot": "Time", "freq_numeric": "Total Incidents"},
        color="freq_numeric",
        color_continuous_scale="Reds"
    )
    st.plotly_chart(fig_time, use_container_width=True)
    
    # By day of week
    day_summary = incidents_df.groupby("day_of_week")["freq_numeric"].sum().reset_index()
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    day_summary["day_of_week"] = pd.Categorical(day_summary["day_of_week"], categories=day_order, ordered=True)
    day_summary = day_summary.sort_values("day_of_week")
    
    fig_day = px.bar(
        day_summary,
        x="day_of_week",
        y="freq_numeric",
        title="Incidents by Day of Week",
        labels={"day_of_week": "Day", "freq_numeric": "Total Incidents"},
        color="freq_numeric",
        color_continuous_scale="Blues"
    )
    st.plotly_chart(fig_day, use_container_width=True)
    
    st.markdown("---")
    
    # Setting/Grouping analysis
    st.markdown("### 7. Context Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if "setting" in incidents_df.columns and not incidents_df["setting"].isna().all():
            setting_summary = incidents_df[incidents_df["setting"] != ""]["setting"].value_counts()
            fig_setting = px.pie(
                values=setting_summary.values,
                names=setting_summary.index,
                title="Incidents by Setting"
            )
            st.plotly_chart(fig_setting, use_container_width=True)
    
    with col2:
        if "grouping" in incidents_df.columns and not incidents_df["grouping"].isna().all():
            grouping_summary = incidents_df[incidents_df["grouping"] != ""]["grouping"].value_counts()
            grouping_labels = [GROUPINGS.get(g, g) for g in grouping_summary.index]
            fig_grouping = px.pie(
                values=grouping_summary.values,
                names=grouping_labels,
                title="Incidents by Grouping"
            )
            st.plotly_chart(fig_grouping, use_container_width=True)
    
    st.markdown("---")
    
    # Scatter plot visualization
    st.markdown("### 8. Scatter Plot Visualization")
    
    # Prepare data for scatter plot
    plot_df = df[df["value"].isin(["1", "2", "3", "4", "5+"])].copy()
    
    if plot_df.empty:
        st.info("No incidents to plot")
    else:
        # Create labels
        plot_df["date_str"] = plot_df["obs_date_dt"].dt.strftime("%a %-d %b")
        
        # Create time labels with activity
        plot_df["time_label"] = plot_df.apply(
            lambda r: f"{r['time_slot']} ({r.get('activity', '-')})", axis=1
        )
        
        # One chart per behaviour
        for beh_idx, beh_label in enumerate(behaviours):
            beh_data = plot_df[plot_df["behaviour_label"] == beh_label].copy()
            
            if beh_data.empty:
                continue
            
            st.markdown(f"#### {beh_label}")
            
            # Unique dates and times for axes
            dates_sorted = sorted(beh_data["date_str"].unique(), key=lambda d: pd.to_datetime(d, format="%a %d %b"))
            times_sorted = sorted(beh_data["time_label"].unique(), key=lambda t: t.split(" ")[0])
            
            fig = go.Figure()
            
            # Add points colored by frequency
            for freq in ["1", "2", "3", "4", "5+"]:
                subset = beh_data[beh_data["value"] == freq]
                if subset.empty:
                    continue
                
                marker_size = {"1": 8, "2": 12, "3": 16, "4": 20, "5+": 24}[freq]
                marker_color = {"1": "#60a5fa", "2": "#fbbf24", "3": "#fb923c", "4": "#f87171", "5+": "#dc2626"}[freq]
                
                fig.add_trace(go.Scatter(
                    x=subset["date_str"],
                    y=subset["time_label"],
                    mode="markers",
                    name=f"{freq} instance(s)",
                    marker=dict(
                        size=marker_size,
                        color=marker_color,
                        opacity=0.8,
                        line=dict(color="white", width=2)
                    ),
                    text=subset.apply(lambda r: f"{r['value']} at {r['time_slot']}<br>{r.get('setting', '')}", axis=1),
                    hovertemplate="%{text}<extra></extra>"
                ))
            
            fig.update_layout(
                title=f"{beh_label} - Scatter Plot",
                xaxis=dict(
                    categoryorder="array",
                    categoryarray=dates_sorted,
                    title="Date",
                    showgrid=True,
                    gridcolor="#e2e8f0"
                ),
                yaxis=dict(
                    categoryorder="array",
                    categoryarray=times_sorted[::-1],
                    title="Time Slot",
                    showgrid=True,
                    gridcolor="#e2e8f0"
                ),
                height=max(400, len(times_sorted) * 25 + 100),
                plot_bgcolor="white",
                paper_bgcolor="white",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                hovermode="closest"
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # ABC Records (if any)
    @st.cache_data(ttl=60, show_spinner=False)
    def load_abc_records(student_name, date_from_str, date_to_str):
        sb = get_sb()
        if not sb: return []
        try:
            res = (sb.table("scatter_abc_records")
                   .select("*")
                   .eq("student_name", student_name)
                   .gte("obs_date", date_from_str)
                   .lte("obs_date", date_to_str)
                   .order("obs_date")
                   .order("time")
                   .execute())
            return res.data or []
        except Exception:
            return []
    
    abc_records = load_abc_records(student_name, str(date_from), str(date_to))
    
    if abc_records:
        st.markdown("### 9. Detailed ABC Records")
        
        for rec in abc_records:
            with st.expander(f"{rec['obs_date']} at {rec['time']} - {rec['behaviour_label']}"):
                st.markdown(f"**Observer:** {rec.get('created_by', '-')}")
                
                st.markdown("<div class='abc-section'><div class='abc-header'>🔹 Antecedent</div>", unsafe_allow_html=True)
                st.markdown(f"**Category:** {rec.get('antecedent_category', '-')}")
                st.markdown(f"**Specific:** {rec.get('antecedent', '-')}")
                if rec.get('antecedent_detail'):
                    st.markdown(f"**Detail:** {rec['antecedent_detail']}")
                st.markdown("</div>", unsafe_allow_html=True)
                
                st.markdown("<div class='abc-section'><div class='abc-header'>🔸 Behaviour</div>", unsafe_allow_html=True)
                st.markdown(f"**Description:** {rec.get('behaviour_description', '-')}")
                st.markdown(f"**Duration:** {rec.get('duration_seconds', 0)} seconds")
                st.markdown(f"**Intensity:** {rec.get('intensity', '-')}")
                st.markdown("</div>", unsafe_allow_html=True)
                
                st.markdown("<div class='abc-section'><div class='abc-header'>🔹 Consequence</div>", unsafe_allow_html=True)
                st.markdown(f"**Category:** {rec.get('consequence_category', '-')}")
                st.markdown(f"**Specific:** {rec.get('consequence', '-')}")
                if rec.get('consequence_detail'):
                    st.markdown(f"**Detail:** {rec['consequence_detail']}")
                st.markdown("</div>", unsafe_allow_html=True)
                
                func = rec.get('observed_function', 'unknown')
                func_label = BEHAVIOUR_FUNCTIONS[func]['label']
                func_class = f"function-tag f-{func}"
                st.markdown(f"<span class='{func_class}'>Function: {func_label}</span>", unsafe_allow_html=True)
        
        st.markdown("---")
    
    # IOA Data (if any)
    if ss.spt_ioa_mode or any("secondary_observer" in rec for rec in data):
        st.markdown("### 10. Inter-Observer Reliability")
        
        ioa_df = df[df.get("secondary_observer", "") != ""].copy()
        
        if not ioa_df.empty:
            st.markdown(f"""
            <div class='ioa-section'>
            <b>IOA Data Collected:</b> {len(ioa_df)} observations with secondary observer<br>
            <small>Use these records to calculate inter-observer agreement following your IOA calculation protocol.</small>
            </div>
            """, unsafe_allow_html=True)
            
            ioa_summary = ioa_df.groupby("secondary_observer").size().reset_index(name="count")
            st.dataframe(
                ioa_summary.rename(columns={"secondary_observer": "Secondary Observer", "count": "Observations"}),
                use_container_width=True,
                hide_index=True
            )
    
    st.markdown("---")
    
    # Download section
    st.markdown("### 11. Export Data")
    
    # CSV export
    csv_data = df.copy()
    csv_data["obs_date"] = csv_data["obs_date_dt"].dt.strftime("%-d/%m/%Y")
    csv_cols = ["obs_date", "day_of_week", "time_slot", "activity", "value", "behaviour_label",
                "setting", "grouping", "created_by"]
    if "observed_function" in csv_data.columns:
        csv_cols.append("observed_function")
    if "secondary_observer" in csv_data.columns:
        csv_cols.append("secondary_observer")
    
    csv = csv_data[csv_cols].to_csv(index=False)
    
    st.download_button(
        "📥 Download Analysis Data (CSV)",
        csv,
        file_name=f"ScatterPlot_ABA_{student_name.replace(' ','_')}_{date_from}_{date_to}.csv",
        mime="text/csv",
        use_container_width=True
    )

st.markdown("---")
st.caption("🏫 Cowandilla Learning Centre - Learning & Behaviour Unit - Scatter Plot Tracker (ABA Edition)")
