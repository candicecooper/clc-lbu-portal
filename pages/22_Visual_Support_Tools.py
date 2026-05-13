# =============================================================================
# 22_Visual_Support_Tools.py  -  CLC-LBU Portal
# Build, customise and print visual supports: lanyard cards, desk mats,
# First-Then boards, visual schedules, communication boards, regulation tools
# PODD-ALIGNED VERSION - Uses PODD vocabulary and symbol structure
# =============================================================================

import streamlit as st
import json
from datetime import datetime

st.set_page_config(
    page_title="Visual Support Tools - CLC",
    page_icon="🎨",
    layout="wide",
)

# -- Brand colours ------------------------------------------------------------
TEAL   = "#1A5C78"
TEAL_L = "#2A8AAF"
TEAL_B = "#EBF5FA"
AMBER  = "#D4860A"
AMB_B  = "#FEF7EA"
GREEN  = "#2D7D4F"
GRN_B  = "#E8F5EE"
NAVY   = "#1A2E44"
CREAM  = "#F7F9FB"

# -- CSS ----------------------------------------------------------------------
st.markdown(f"""
<style>
[data-testid="stAppViewContainer"] {{ background:{CREAM}; }}

.vst-header {{
    background:linear-gradient(135deg,{TEAL} 0%,#0F3D54 100%);
    color:#fff; padding:1rem 1.5rem; border-radius:12px;
    margin-bottom:1.5rem; display:flex; align-items:center; gap:1rem;
}}
.vst-header .icon {{ font-size:2.2rem; }}
.vst-header h1 {{ margin:0; font-size:1.35rem; font-weight:800; }}
.vst-header p  {{ margin:.1rem 0 0; opacity:.8; font-size:.82rem; }}

.section-card {{
    background:#fff; border-radius:12px; border:1px solid #dde6ee;
    padding:1.1rem 1.3rem; margin-bottom:1rem;
    box-shadow:0 2px 8px rgba(0,0,0,.06);
}}
.section-card h3 {{
    margin:0 0 .75rem; font-size:1rem; font-weight:800; color:{TEAL};
}}

.vc {{
    background:#fff; border-radius:10px; border:2px solid #dde6ee;
    padding:.85rem .6rem; text-align:center; min-height:120px;
    display:flex; flex-direction:column; justify-content:center;
}}
.vc .em {{ font-size:2.4rem; line-height:1; margin-bottom:.45rem; }}
.vc .ti {{ font-size:.88rem; font-weight:700; color:{NAVY}; line-height:1.25; }}
.vc .su {{ font-size:.73rem; color:#718096; margin-top:.25rem; }}

.fw {{
    display:inline-block; padding:.1rem .42rem; border-radius:20px;
    font-size:.62rem; font-weight:700; margin:.1rem .1rem 0 0;
}}

.slot {{
    border:2px dashed #cbd5e0; border-radius:10px;
    min-height:130px; display:flex; flex-direction:column;
    align-items:center; justify-content:center; padding:1rem;
    text-align:center; background:#f8fafc;
}}
.slot.filled {{
    border-style:solid; border-color:{TEAL}; background:{TEAL_B};
}}
.slot .slot-lbl {{
    font-size:.65rem; font-weight:800; text-transform:uppercase;
    letter-spacing:.1em; color:#718096; margin-bottom:.4rem;
}}
.slot.filled .slot-lbl {{ color:{TEAL}; }}
.slot .slot-em {{ font-size:2.5rem; line-height:1; margin-bottom:.3rem; }}
.slot .slot-tx {{ font-size:.88rem; font-weight:700; }}

.zone {{ border-radius:10px; padding:.85rem; border:2px solid transparent; margin-bottom:.5rem; }}
.zone-blue   {{ background:#DBEAFE; border-color:#93C5FD; }}
.zone-green  {{ background:#DCFCE7; border-color:#86EFAC; }}
.zone-yellow {{ background:#FEF9C3; border-color:#FDE047; }}
.zone-red    {{ background:#FEE2E2; border-color:#FCA5A5; }}
.zone h4     {{ margin:0 0 .4rem; font-size:.9rem; font-weight:800; }}
.zone .feels {{ font-size:.75rem; color:#4a5568; line-height:1.7; }}

.research-note {{
    background:{TEAL_B}; border:1px solid {TEAL}; border-radius:8px;
    padding:.6rem .9rem; font-size:.8rem; color:{TEAL}; margin-top:.75rem;
}}

.podd-note {{
    background:#FEF7EA; border:1px solid #D4860A; border-radius:8px;
    padding:.8rem 1rem; font-size:.82rem; color:#8C5A0A; margin:1rem 0;
    line-height:1.6;
}}
.podd-note strong {{ color:#D4860A; }}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# DATA - PODD-ALIGNED VOCABULARY
# =============================================================================

# Note: This structure supports both emoji fallbacks AND PODD symbol URLs
# To use actual PODD symbols, populate the 'podd_symbol' field with image URLs
# from your licensed PODD symbol library

CARDS = [
    # Regulation - PODD uses "I feel..." language
    dict(id="feelings",   cat="regulation",    color=AMBER,     em="😊😐😢😠", podd_symbol=None, ti="I feel",        sub="Tell someone",      fw=["BSEM","ZOR","TI"]),
    dict(id="help",       cat="regulation",    color=AMBER,     em="🤝",        podd_symbol=None, ti="I need help",           sub="Someone help me",        fw=["BSEM","TI","AAC"]),
    dict(id="break",      cat="regulation",    color=AMBER,     em="⏸️",        podd_symbol=None, ti="I need a break",           sub="I want to stop",           fw=["TI","PBS","BSEM"]),
    dict(id="calm",       cat="regulation",    color=AMBER,     em="🧘",        podd_symbol=None, ti="I need to calm down",      sub="I want quiet",            fw=["BSEM","TI","OT"]),
    dict(id="safe",       cat="regulation",    color=AMBER,     em="🛡️",        podd_symbol=None, ti="I feel safe",          sub="It's okay",         fw=["TI","PBS"]),
    
    # Communication - PODD core vocabulary
    dict(id="yes",        cat="communication", color="#2D7D4F", em="✅",        podd_symbol=None, ti="Yes",                    sub="I want this",             fw=["AAC","PODD"]),
    dict(id="no",         cat="communication", color="#2D7D4F", em="❌",        podd_symbol=None, ti="No",                     sub="I don't want this",       fw=["AAC","PODD"]),
    dict(id="more",       cat="communication", color="#2D7D4F", em="➕",        podd_symbol=None, ti="More",                   sub="I want more",             fw=["AAC","PODD"]),
    dict(id="finished",   cat="communication", color="#2D7D4F", em="✔️",        podd_symbol=None, ti="Finished",               sub="All done",                fw=["AAC","PODD"]),
    dict(id="want",       cat="communication", color="#2D7D4F", em="🎯",        podd_symbol=None, ti="I want",                 sub="Something I want",        fw=["AAC","PODD"]),
    dict(id="like",       cat="communication", color="#2D7D4F", em="👍",        podd_symbol=None, ti="I like",                 sub="Something I like",        fw=["AAC","PODD"]),
    dict(id="dont_like",  cat="communication", color="#2D7D4F", em="👎",        podd_symbol=None, ti="I don't like",           sub="Something I don't like",  fw=["AAC","PODD"]),
    
    # Actions - PODD uses "I want to..." language
    dict(id="go",         cat="actions",       color="#3730A3", em="🚶",        podd_symbol=None, ti="I want to go",           sub="I want to move",          fw=["AAC","PODD"]),
    dict(id="stop",       cat="actions",       color="#3730A3", em="🛑",        podd_symbol=None, ti="I want to stop",         sub="Stop now",                fw=["AAC","PODD"]),
    dict(id="wait",       cat="actions",       color="#3730A3", em="⏱️",        podd_symbol=None, ti="I can wait",             sub="Wait please",             fw=["AAC","PODD"]),
    dict(id="look",       cat="actions",       color="#3730A3", em="👀",        podd_symbol=None, ti="I want to look",         sub="I want to see",           fw=["AAC","PODD"]),
    dict(id="listen",     cat="actions",       color="#3730A3", em="👂",        podd_symbol=None, ti="I want to listen",       sub="I want to hear",          fw=["AAC","PODD"]),
    
    # Social - PODD social interaction vocabulary
    dict(id="hello",      cat="social",        color="#8C2D5A", em="👋",        podd_symbol=None, ti="Hello",                  sub="Say hi",                  fw=["AAC","PODD"]),
    dict(id="goodbye",    cat="social",        color="#8C2D5A", em="👋",        podd_symbol=None, ti="Goodbye",                sub="Say bye",                 fw=["AAC","PODD"]),
    dict(id="please",     cat="social",        color="#8C2D5A", em="🙏",        podd_symbol=None, ti="Please",                 sub="Can I have please",       fw=["AAC","PODD"]),
    dict(id="thankyou",   cat="social",        color="#8C2D5A", em="💝",        podd_symbol=None, ti="Thank you",              sub="Thanks",                  fw=["AAC","PODD"]),
    dict(id="sorry",      cat="social",        color="#8C2D5A", em="🙇",        podd_symbol=None, ti="Sorry",                  sub="I am sorry",              fw=["AAC","PODD"]),
    
    # Places - PODD location vocabulary
    dict(id="bathroom",   cat="places",        color="#0E7490", em="🚻",        podd_symbol=None, ti="Bathroom",               sub="I want the toilet",       fw=["AAC","PODD"]),
    dict(id="outside",    cat="places",        color="#0E7490", em="🌳",        podd_symbol=None, ti="Outside",                sub="I want to go outside",    fw=["AAC","PODD"]),
    dict(id="home",       cat="places",        color="#0E7490", em="🏠",        podd_symbol=None, ti="Home",                   sub="I want to go home",       fw=["AAC","PODD"]),
    
    # Activities - PODD activity vocabulary  
    dict(id="eat",        cat="activities",    color="#059669", em="🍽️",        podd_symbol=None, ti="I want to eat",          sub="Food",                    fw=["AAC","PODD"]),
    dict(id="drink",      cat="activities",    color="#059669", em="🥤",        podd_symbol=None, ti="I want to drink",        sub="Something to drink",      fw=["AAC","PODD"]),
    dict(id="play",       cat="activities",    color="#059669", em="🎮",        podd_symbol=None, ti="I want to play",         sub="Play time",               fw=["AAC","PODD"]),
    dict(id="work",       cat="activities",    color="#059669", em="📝",        podd_symbol=None, ti="I want to work",         sub="Do work",                 fw=["AAC","PODD"]),
    dict(id="read",       cat="activities",    color="#059669", em="📚",        podd_symbol=None, ti="I want to read",         sub="Read a book",             fw=["AAC","PODD"]),
]

# PODD-aligned feelings vocabulary
FEELINGS_PODD = [
    ("😊", "happy"),
    ("😢", "sad"),
    ("😠", "angry"),
    ("😰", "scared"),
    ("😴", "tired"),
    ("🤗", "excited"),
    ("😐", "okay"),
    ("😕", "worried"),
]

# PODD-aligned calm down strategies using "I can..." language
CALM_STRATEGIES_PODD = [
    dict(em="🫁", lb="I can breathe"),
    dict(em="🚶", lb="I can walk"),
    dict(em="💺", lb="I can sit"),
    dict(em="🤲", lb="I can squeeze"),
    dict(em="💧", lb="I can drink water"),
    dict(em="🎵", lb="I can listen"),
    dict(em="📖", lb="I can look"),
    dict(em="🤗", lb="I can hug"),
    dict(em="✋", lb="I can stop"),
]

# Framework details
FW_DETAILS = {
    "BSEM":  {"label":"BSEM",  "bg":"#1A5C78","color":"#fff"},
    "ZOR":   {"label":"ZOR",   "bg":"#2D7D4F","color":"#fff"},
    "TI":    {"label":"TI",    "bg":"#D4860A","color":"#fff"},
    "PBS":   {"label":"PBS",   "bg":"#8C2D5A","color":"#fff"},
    "OT":    {"label":"OT",    "bg":"#0E7490","color":"#fff"},
    "AAC":   {"label":"AAC",   "bg":"#7C2D91","color":"#fff"},
    "PODD":  {"label":"PODD",  "bg":"#059669","color":"#fff"},
}

# Zones of Regulation
ZONE_DATA = {
    "blue":   {"name":"Blue - Moving Slowly",  "bg":"#DBEAFE","color":"#1E40AF","feels":["tired","sad","sick","bored"]},
    "green":  {"name":"Green - Ready to Learn","bg":"#DCFCE7","color":"#15803D","feels":["happy","calm","okay","focused"]},
    "yellow": {"name":"Yellow - Losing Control","bg":"#FEF9C3","color":"#A16207","feels":["frustrated","worried","silly","excited"]},
    "red":    {"name":"Red - Out of Control","bg":"#FEE2E2","color":"#B91C1C","feels":["angry","scared","yelling","upset"]},
}

FIVE_COLORS = ["#93C5FD","#86EFAC","#FDE047","#FDBA74","#F87171"]
FIVE_EMOJIS = ["😊","😀","😐","😟","😭"]

# =============================================================================
# INTERFACE
# =============================================================================

st.markdown("""
<div class="vst-header">
    <div class="icon">🎨</div>
    <div>
        <h1>Visual Support Tools</h1>
        <p>Create PODD-aligned communication supports • Build • Customise • Print</p>
    </div>
</div>
""", unsafe_allow_html=True)

# PODD Information Notice
st.markdown("""
<div class="podd-note">
    <strong>PODD-Aligned Design:</strong> This tool uses vocabulary and language structures aligned with 
    Pragmatic Organisation Dynamic Display (PODD) principles. Cards use AAC-appropriate language 
    with core vocabulary like "I want", "I feel", "I need". To use actual PODD symbols, add image URLs 
    to the <code>podd_symbol</code> field in the card data structure.
</div>
""", unsafe_allow_html=True)

tabs = st.tabs([
    "📇 Quick Cards",
    "➡️ First-Then Boards", 
    "📅 Visual Schedules",
    "💬 Communication Boards",
    "🧘 Regulation Tools",
    "📜 Social Scripts",
    "🖨️ Print Queue"
])

# Initialize session state
if "vst_print_queue" not in st.session_state:
    st.session_state.vst_print_queue = []

# TAB 1: Quick Cards --------------------------------------------------------
with tabs[0]:
    st.markdown('<div class="section-card"><h3>Select Quick Cards</h3></div>', unsafe_allow_html=True)
    
    cats = {"regulation":"🧘 Regulation","communication":"💬 Communication","actions":"🎯 Actions",
            "social":"🤝 Social","places":"📍 Places","activities":"✨ Activities"}
    
    for cat_id, cat_name in cats.items():
        cat_cards = [c for c in CARDS if c.get("cat") == cat_id]
        if cat_cards:
            with st.expander(f"{cat_name} ({len(cat_cards)} cards)", expanded=(cat_id=="regulation")):
                cols = st.columns(4)
                for i, c in enumerate(cat_cards):
                    with cols[i % 4]:
                        # Show PODD symbol or emoji fallback
                        symbol = c.get("podd_symbol") or c.get("em", "📌")
                        fws = "".join(
                            f'<span class="fw" style="background:{FW_DETAILS.get(f,{}).get("bg","#eee")};color:{FW_DETAILS.get(f,{}).get("color","#333")}">{FW_DETAILS.get(f,{}).get("label",f)}</span>'
                            for f in c.get("fw",[])
                        )
                        st.markdown(f"""<div class="vc" style="border-color:{c.get('color',TEAL)}">
                            <div class="em">{symbol}</div>
                            <div class="ti">{c.get('ti','')}</div>
                            <div class="su">{c.get('sub','')}</div>
                            <div style="margin-top:.3rem">{fws}</div>
                        </div>""", unsafe_allow_html=True)
                        
                        if st.button(f"Add to print", key=f"add_{c['id']}", use_container_width=True):
                            st.session_state.vst_print_queue.append({"type":"cards","data":[c]})
                            st.success("✅ Added to print queue")
                            st.rerun()

# TAB 2: First-Then Boards ---------------------------------------------------
with tabs[1]:
    st.markdown('<div class="section-card"><h3>Build First-Then Board</h3></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        ft_student = st.text_input("Student name (optional)", key="ft_student")
        ft_title = st.text_input("Board title", value="First-Then", key="ft_title")
        ft_steps = st.radio("Number of steps", [2,3,4], horizontal=True, key="ft_steps")
    
    with col2:
        st.markdown("**PODD Tip:** Use action vocabulary like 'I want to...', 'I can...', 'I will...'")
    
    ft_labels = ["FIRST","THEN","NEXT","LAST"][:ft_steps]
    ft_slots = []
    
    cols = st.columns(ft_steps)
    for i, lbl in enumerate(ft_labels):
        with cols[i]:
            st.markdown(f'<div class="slot-lbl">{lbl}</div>', unsafe_allow_html=True)
            slot_cards = [{"em":c.get("em"),"lb":c.get("ti"),"id":c.get("id")} for c in CARDS]
            sel = st.selectbox(f"Select activity", 
                             options=[None]+slot_cards,
                             format_func=lambda x: f"{x['em']} {x['lb']}" if x else "-- Choose --",
                             key=f"ft_slot_{i}")
            ft_slots.append(sel)
    
    if st.button("➕ Add First-Then to Print", type="primary", use_container_width=True):
        if all(s is not None for s in ft_slots):
            st.session_state.vst_print_queue.append({
                "type":"firstthen",
                "data":{"student":ft_student,"title":ft_title,"labels":ft_labels,"slots":ft_slots}
            })
            st.success("✅ Added to print queue")
            st.rerun()
        else:
            st.error("Please fill all slots")

# TAB 3: Visual Schedules ----------------------------------------------------
with tabs[2]:
    st.markdown('<div class="section-card"><h3>Build Visual Schedule</h3></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2,3])
    with col1:
        vs_student = st.text_input("Student name (optional)", key="vs_student")
        vs_title = st.text_input("Schedule title", value="My Schedule", key="vs_title")
        vs_slots_n = st.number_input("Number of activities", min_value=3, max_value=12, value=6, key="vs_slots_n")
    
    with col2:
        st.markdown("**PODD Schedule Language:** Use 'I will...', 'Time to...', 'Next I...'")
    
    vs_slots = []
    for i in range(vs_slots_n):
        col_t, col_a = st.columns([1,2])
        with col_t:
            time = st.text_input(f"Time", value=f"{8+i}:00", key=f"vs_time_{i}", label_visibility="collapsed")
        with col_a:
            activity_cards = [{"em":c.get("em"),"lb":c.get("ti"),"id":c.get("id")} for c in CARDS]
            sel = st.selectbox(f"Activity {i+1}",
                             options=[None]+activity_cards,
                             format_func=lambda x: f"{x['em']} {x['lb']}" if x else "-- Choose --",
                             key=f"vs_act_{i}",
                             label_visibility="collapsed")
            if sel:
                vs_slots.append({"time":time,"em":sel["em"],"act":sel["lb"]})
    
    if st.button("➕ Add Schedule to Print", type="primary", use_container_width=True):
        if vs_slots:
            st.session_state.vst_print_queue.append({
                "type":"schedule",
                "data":{"student":vs_student,"title":vs_title,"slots":vs_slots}
            })
            st.success("✅ Added to print queue")
            st.rerun()
        else:
            st.error("Add at least one activity")

# TAB 4: Communication Boards ------------------------------------------------
with tabs[3]:
    st.markdown('<div class="section-card"><h3>Build Communication Board</h3></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2,3])
    with col1:
        cb_title = st.text_input("Board title", value="I want to tell you", key="cb_title")
        cb_grid = st.selectbox("Grid size", ["2x2","2x3","3x3","3x4","4x4"], index=2, key="cb_grid")
    
    with col2:
        st.markdown("**PODD Core Board:** Include core vocabulary: yes, no, more, help, I want, I feel")
    
    cb_cells = []
    cols_n, rows_n = map(int, cb_grid.split("x"))
    total = cols_n * rows_n
    
    board_cards = [{"em":c.get("em"),"tx":c.get("ti"),"id":c.get("id")} for c in CARDS]
    
    cols = st.columns(cols_n)
    for i in range(total):
        with cols[i % cols_n]:
            sel = st.selectbox(f"Cell {i+1}",
                             options=[None]+board_cards,
                             format_func=lambda x: f"{x['em']} {x['tx']}" if x else "-- Empty --",
                             key=f"cb_cell_{i}",
                             label_visibility="collapsed")
            cb_cells.append(sel if sel else {"em":"","tx":""})
    
    if st.button("➕ Add Communication Board to Print", type="primary", use_container_width=True):
        st.session_state.vst_print_queue.append({
            "type":"board",
            "data":{"title":cb_title,"gridSize":cb_grid,"cells":cb_cells}
        })
        st.success("✅ Added to print queue")
        st.rerun()

# TAB 5: Regulation Tools ----------------------------------------------------
with tabs[4]:
    st.markdown('<div class="section-card"><h3>Build Regulation Tool</h3></div>', unsafe_allow_html=True)
    
    tool_type = st.radio("Select tool type", 
                        ["Zones of Regulation","5-Point Scale","Feelings Chart","Calm-Down Toolkit"],
                        horizontal=True)
    
    if tool_type == "Zones of Regulation":
        st.markdown("**Zones of Regulation** - PODD language: 'I feel', 'I am in the...'")
        for zone, zd in ZONE_DATA.items():
            st.markdown(f"""<div class="zone zone-{zone}">
                <h4>{zd['name']}</h4>
                <div class="feels">{' • '.join(zd['feels'])}</div>
            </div>""", unsafe_allow_html=True)
        
        if st.button("➕ Add Zones Card to Print", use_container_width=True):
            st.session_state.vst_print_queue.append({
                "type":"regulation",
                "data":{"tool":"zones"}
            })
            st.success("✅ Added to print queue")
            st.rerun()
    
    elif tool_type == "5-Point Scale":
        st.markdown("**5-Point Scale** - PODD: 'I feel', 'My body is', 'I can...'")
        fp_student = st.text_input("Student name (optional)", key="fp_student")
        fp_labels = []
        cols = st.columns(5)
        for i in range(5):
            with cols[i]:
                st.markdown(f'<div style="text-align:center;font-size:2rem">{FIVE_EMOJIS[i]}</div>', unsafe_allow_html=True)
                lbl = st.text_input(f"Level {i+1}", value=["calm","okay","worried","upset","very upset"][i], key=f"fp_lbl_{i}", label_visibility="collapsed")
                fp_labels.append(lbl)
        
        if st.button("➕ Add 5-Point Scale to Print", use_container_width=True):
            st.session_state.vst_print_queue.append({
                "type":"regulation",
                "data":{"tool":"fivepoint","student":fp_student,"labels":fp_labels}
            })
            st.success("✅ Added to print queue")
            st.rerun()
    
    elif tool_type == "Feelings Chart":
        st.markdown("**Feelings Chart** - PODD: 'I feel...' language")
        
        fc_selected = st.multiselect("Select feelings to include",
                                    options=FEELINGS_PODD,
                                    default=FEELINGS_PODD[:4],
                                    format_func=lambda x: f"{x[0]} {x[1]}",
                                    key="fc_feelings")
        
        if st.button("➕ Add Feelings Chart to Print", use_container_width=True):
            if fc_selected:
                st.session_state.vst_print_queue.append({
                    "type":"regulation",
                    "data":{"tool":"feelings","feels":fc_selected}
                })
                st.success("✅ Added to print queue")
                st.rerun()
            else:
                st.error("Select at least one feeling")
    
    elif tool_type == "Calm-Down Toolkit":
        st.markdown("**Calm-Down Toolkit** - PODD: 'I can...' strategies")
        cd_title = st.text_input("Toolkit title", value="I can calm down", key="cd_title")
        
        cd_strats = st.multiselect("Select strategies",
                                   options=CALM_STRATEGIES_PODD,
                                   default=CALM_STRATEGIES_PODD[:6],
                                   format_func=lambda x: f"{x['em']} {x['lb']}",
                                   key="cd_strats")
        
        if st.button("➕ Add Calm-Down Toolkit to Print", use_container_width=True):
            if cd_strats:
                st.session_state.vst_print_queue.append({
                    "type":"regulation",
                    "data":{"tool":"calmdown","title":cd_title,"strats":cd_strats}
                })
                st.success("✅ Added to print queue")
                st.rerun()
            else:
                st.error("Select at least one strategy")

# TAB 6: Social Scripts ------------------------------------------------------
with tabs[5]:
    st.markdown('<div class="section-card"><h3>Build Social Script</h3></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2,3])
    with col1:
        ss_student = st.text_input("Student name (optional)", key="ss_student")
        ss_title = st.text_input("Script title", value="How to ask for help", key="ss_title")
        ss_steps_n = st.number_input("Number of steps", min_value=2, max_value=8, value=4, key="ss_steps_n")
    
    with col2:
        st.markdown("**PODD Social Script:** Use 'I will...', 'I can...', 'Someone will...'")
    
    ss_steps = []
    for i in range(ss_steps_n):
        col_e, col_t = st.columns([1,4])
        with col_e:
            em = st.text_input(f"Emoji {i+1}", value=["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣"][i], key=f"ss_em_{i}", label_visibility="collapsed")
        with col_t:
            tx = st.text_input(f"Step {i+1}", key=f"ss_tx_{i}", label_visibility="collapsed", 
                             placeholder="e.g., I will tell someone I need help")
        if tx:
            ss_steps.append({"em":em,"tx":tx})
    
    if st.button("➕ Add Social Script to Print", type="primary", use_container_width=True):
        if ss_steps:
            st.session_state.vst_print_queue.append({
                "type":"script",
                "data":{"student":ss_student,"title":ss_title,"steps":ss_steps}
            })
            st.success("✅ Added to print queue")
            st.rerun()
        else:
            st.error("Add at least one step")

# TAB 7: Print Queue ---------------------------------------------------------
with tabs[6]:
    st.markdown('<div class="section-card"><h3>Print Queue</h3></div>', unsafe_allow_html=True)
    
    if not st.session_state.vst_print_queue:
        st.info("📭 Print queue is empty. Add items from other tabs.")
    else:
        st.markdown(f"**{len(st.session_state.vst_print_queue)} item(s) in queue**")
        
        for i, item in enumerate(st.session_state.vst_print_queue):
            col1, col2 = st.columns([5,1])
            with col1:
                t = item["type"]
                d = item["data"]
                if t == "cards":
                    st.markdown(f"📇 **Quick Cards** ({len(d)} cards)")
                elif t == "firstthen":
                    st.markdown(f"➡️ **First-Then:** {d.get('title','')}")
                elif t == "schedule":
                    st.markdown(f"📅 **Schedule:** {d.get('title','')} ({len(d.get('slots',[]))} activities)")
                elif t == "board":
                    st.markdown(f"💬 **Comm Board:** {d.get('title','')}")
                elif t == "regulation":
                    tool_names = {"zones":"Zones of Regulation","fivepoint":"5-Point Scale",
                                "feelings":"Feelings Chart","calmdown":"Calm-Down Toolkit"}
                    st.markdown(f"🧘 **Regulation:** {tool_names.get(d.get('tool',''),'')}")
                elif t == "script":
                    st.markdown(f"📜 **Social Script:** {d.get('title','')}")
            
            with col2:
                if st.button("🗑️", key=f"del_{i}"):
                    st.session_state.vst_print_queue.pop(i)
                    st.rerun()
        
        st.divider()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🗑️ Clear all", use_container_width=True):
                st.session_state.vst_print_queue = []
                st.rerun()
        
        with col2:
            fmt = st.selectbox("Print format", ["A4 Cards (4 per page)","Lanyard Cards (8 per page)"], key="print_fmt")
        
        with col3:
            is_lanyard = "Lanyard" in fmt
            page_size = "85mm 54mm" if is_lanyard else "A4 portrait"
            card_h = "54mm" if is_lanyard else "140mm"
            em_sz = "18px" if is_lanyard else "28px"
            ti_sz = "9px" if is_lanyard else "14px"
            su_sz = "7px" if is_lanyard else "10px"
            fw_sz = "5.5px" if is_lanyard else "7px"

            def card_html(c):
                # Use PODD symbol if available, otherwise fallback to emoji
                symbol = c.get('podd_symbol') or c.get('em', '📌')
                
                fws = "".join(
                    f'<span style="background:{FW_DETAILS.get(f,{}).get("bg","#eee")};color:{FW_DETAILS.get(f,{}).get("color","#333")};padding:1px 5px;border-radius:10px;font-size:{fw_sz};font-weight:700;margin-right:2px">{FW_DETAILS.get(f,{}).get("label",f)}</span>'
                    for f in c.get("fw",[])
                )
                return f"""<div style="border:1.5px solid #dde;border-radius:8px;min-height:{card_h};overflow:hidden;display:flex;flex-direction:column;position:relative">
                  <div style="height:5px;background:{c.get('color',TEAL)}"></div>
                  <div style="height:8px;width:8px;border-radius:50%;border:1.5px solid #dde;position:absolute;top:3px;left:50%;transform:translateX(-50%);background:#fff"></div>
                  <div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:6px 5px;text-align:center">
                    <div style="font-size:{em_sz};line-height:1;margin-bottom:4px">{symbol}</div>
                    <div style="font-size:{ti_sz};font-weight:800;color:#1a2e44;line-height:1.2">{c.get('ti','')}</div>
                    <div style="font-size:{su_sz};color:#718096;margin-top:2px">{c.get('sub','')}</div>
                    <div style="margin-top:3px">{fws}</div>
                  </div>
                </div>"""

            all_cards_html = []

            for item in st.session_state.vst_print_queue:
                t = item["type"]
                d = item["data"]

                if t == "cards":
                    for c in d:
                        all_cards_html.append(card_html(c))

                elif t == "firstthen":
                    slots_html = ""
                    for si, (lbl, slot) in enumerate(zip(d["labels"], d["slots"])):
                        if si > 0:
                            slots_html += '<div style="font-size:16px;color:#718096;display:flex;align-items:center">&#8594;</div>'
                        symbol = slot.get("em","?") if slot else "?"
                        slots_html += f'<div style="flex:1;border:1px solid #eee;border-radius:4px;background:#f8f9fa;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:4px 3px;text-align:center"><div style="font-size:6px;font-weight:800;text-transform:uppercase;color:#718096;margin-bottom:2px">{lbl}</div><div style="font-size:{em_sz}">{symbol}</div><div style="font-size:8px;font-weight:700;margin-top:1px">{slot["lb"] if slot else ""}</div></div>'
                    name = d.get("student","")
                    all_cards_html.append(f'<div style="border:1.5px solid #dde;border-radius:8px;min-height:{card_h};overflow:hidden;display:flex;flex-direction:column"><div style="height:5px;background:{GREEN}"></div><div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:5px"><div style="font-size:8px;font-weight:800;color:#1a2e44;margin-bottom:4px">{(name + "\'s ") if name else ""}{d.get("title","")}</div><div style="display:flex;gap:3px;align-items:center;width:100%">{slots_html}</div></div></div>')

                elif t == "schedule":
                    slots_rows = "".join(
                        f'<div style="display:flex;align-items:center;gap:3px;padding:2px 5px;border-bottom:1px solid #f0f0f0"><span style="font-size:{"6px" if is_lanyard else "8px"};font-weight:700;color:#718096;min-width:28px">{s.get("time","")}</span><span style="font-size:{"11px" if is_lanyard else "16px"}">{s.get("em","")}</span><span style="font-size:{"7px" if is_lanyard else "10px"};font-weight:700">{s.get("act","")}</span></div>'
                        for s in d.get("slots",[])[:7]
                    )
                    name = d.get("student","")
                    all_cards_html.append(f'<div style="border:1.5px solid #dde;border-radius:8px;min-height:{card_h};overflow:hidden;display:flex;flex-direction:column"><div style="height:5px;background:{TEAL}"></div><div style="flex:1;display:flex;flex-direction:column;padding:3px 0"><div style="text-align:center;font-size:8px;font-weight:800;color:#1a2e44;padding:2px 5px 3px">{(name + "\'s ") if name else ""}{d.get("title","Schedule")}</div>{slots_rows}</div></div>')

                elif t == "board":
                    cols_n = int(d["gridSize"].split("x")[0])
                    cells_html = "".join(
                        f'<div style="border:1px solid #dde;border-radius:3px;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:2px;text-align:center"><span style="font-size:{"13px" if is_lanyard else "18px"}">{c.get("em","")}</span><span style="font-size:{"5.5px" if is_lanyard else "8px"};font-weight:700">{c.get("tx","")}</span></div>'
                        for c in d.get("cells",[])
                    )
                    all_cards_html.append(f'<div style="border:1.5px solid #dde;border-radius:8px;min-height:{card_h};overflow:hidden;display:flex;flex-direction:column"><div style="height:5px;background:#8C2D5A"></div><div style="flex:1;display:flex;flex-direction:column;padding:3px"><div style="text-align:center;font-size:8px;font-weight:800;margin-bottom:2px">{d.get("title","Comm Board")}</div><div style="display:grid;grid-template-columns:repeat({cols_n},1fr);gap:2px;flex:1">{cells_html}</div></div></div>')

                elif t == "regulation":
                    tool = d.get("tool","")
                    if tool == "zones":
                        zboxes = "".join(
                            f'<div style="background:{zd["bg"]};border-radius:3px;padding:2px 3px"><div style="font-size:7px;font-weight:800;color:{zd["color"]}">{zd["name"].split(" - ")[0]}</div><div style="font-size:5.5px;line-height:1.4">{" / ".join(zd["feels"][:2])}</div></div>'
                            for z, zd in ZONE_DATA.items()
                        )
                        all_cards_html.append(f'<div style="border:1.5px solid #dde;border-radius:8px;min-height:{card_h};overflow:hidden;display:flex;flex-direction:column"><div style="height:5px;background:linear-gradient(to right,#3B82F6,#22C55E,#EAB308,#EF4444)"></div><div style="flex:1;padding:4px;display:flex;flex-direction:column"><div style="text-align:center;font-size:8px;font-weight:800;margin-bottom:3px">Zones of Regulation</div><div style="display:grid;grid-template-columns:1fr 1fr;gap:2px;flex:1">{zboxes}</div></div></div>')
                    elif tool == "fivepoint":
                        pts = "".join(f'<div style="flex:1;background:{FIVE_COLORS[i]};border-radius:4px;text-align:center;padding:2px"><div style="font-size:11px">{FIVE_EMOJIS[i]}</div><div style="font-size:8px;font-weight:900">{i+1}</div><div style="font-size:5px;font-weight:600">{d.get("labels",[])[i] if i < len(d.get("labels",[])) else ""}</div></div>' for i in range(5))
                        name = d.get("student","")
                        all_cards_html.append(f'<div style="border:1.5px solid #dde;border-radius:8px;min-height:{card_h};overflow:hidden;display:flex;flex-direction:column"><div style="height:5px;background:{TEAL}"></div><div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:5px"><div style="font-size:8px;font-weight:800;margin-bottom:4px">{(name + "\'s ") if name else ""}5-Point Scale</div><div style="display:flex;gap:2px;width:100%">{pts}</div></div></div>')
                    elif tool == "calmdown":
                        sh = "".join(f'<div style="text-align:center;padding:1px"><div style="font-size:12px">{s["em"]}</div><div style="font-size:5.5px;font-weight:700">{s["lb"]}</div></div>' for s in d.get("strats",[])[:9])
                        all_cards_html.append(f'<div style="border:1.5px solid #dde;border-radius:8px;min-height:{card_h};overflow:hidden;display:flex;flex-direction:column"><div style="height:5px;background:{GREEN}"></div><div style="flex:1;padding:4px;display:flex;flex-direction:column"><div style="text-align:center;font-size:8px;font-weight:800;margin-bottom:2px">{d.get("title","Calm-Down Toolkit")}</div><div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1px;flex:1">{sh}</div></div></div>')
                    elif tool == "feelings":
                        n_c = len(d.get("feels",[])) or 4
                        fh = "".join(f'<div style="text-align:center;padding:2px;border:1px solid #dde;border-radius:3px"><div style="font-size:{"11px" if is_lanyard else "16px"}">{em}</div><div style="font-size:{"5.5px" if is_lanyard else "7px"};font-weight:700">{tx}</div></div>' for em, tx in d.get("feels",[]))
                        all_cards_html.append(f'<div style="border:1.5px solid #dde;border-radius:8px;min-height:{card_h};overflow:hidden;display:flex;flex-direction:column"><div style="height:5px;background:{AMBER}"></div><div style="flex:1;padding:4px;display:flex;flex-direction:column"><div style="text-align:center;font-size:8px;font-weight:800;margin-bottom:2px">I feel</div><div style="display:grid;grid-template-columns:repeat({min(n_c,4)},1fr);gap:2px;flex:1">{fh}</div></div></div>')

                elif t == "script":
                    steps_html = "".join(
                        f'<div style="display:flex;align-items:flex-start;gap:2px;margin-bottom:1px"><div style="min-width:12px;height:12px;border-radius:50%;background:{TEAL};color:#fff;font-size:6px;font-weight:800;display:flex;align-items:center;justify-content:center">{i+1}</div><div style="font-size:{"6px" if is_lanyard else "8px"};font-weight:600;line-height:1.3">{s["em"]} {s["tx"]}</div></div>'
                        for i, s in enumerate(d.get("steps",[])[:5])
                    )
                    name = d.get("student","")
                    all_cards_html.append(f'<div style="border:1.5px solid #dde;border-radius:8px;min-height:{card_h};overflow:hidden;display:flex;flex-direction:column"><div style="height:5px;background:#3730A3"></div><div style="flex:1;padding:4px;display:flex;flex-direction:column"><div style="text-align:center;font-size:8px;font-weight:800;margin-bottom:3px">{(name + "\'s ") if name else ""}{d.get("title","Social Script")}</div>{steps_html}</div></div>')

            per_row = 2
            per_page = 8 if is_lanyard else 4
            pages = [all_cards_html[i:i+per_page] for i in range(0, len(all_cards_html), per_page)]

            def make_page(cards):
                rows_h = ""
                for ri in range(0, len(cards), per_row):
                    row_cards = cards[ri:ri+per_row]
                    cols_html = "".join(f'<td style="width:50%;padding:2mm;vertical-align:top">{c}</td>' for c in row_cards)
                    rows_h += f"<tr>{cols_html}</tr>"
                return f'<table style="width:100%;border-collapse:collapse;page-break-after:always">{rows_h}</table>'

            print_html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>*{{box-sizing:border-box;margin:0;padding:0;font-family:'Nunito',sans-serif}}@page{{size:{page_size};margin:6mm}}body{{background:#fff}}</style>
</head><body>{"".join(make_page(p) for p in pages)}</body></html>"""

            st.download_button(
                label="⬇️ Download print HTML",
                data=print_html,
                file_name=f"visual_supports_PODD_{fmt.replace(' ','_').lower()}.html",
                mime="text/html",
            )
            st.info("📄 Open the downloaded file in Chrome then use File > Print (Ctrl+P). Set margins to None and enable Background graphics.")
            
            st.markdown("""
            <div class="podd-note">
                <strong>PODD Symbol Integration:</strong> To display actual PODD symbols instead of emojis, 
                add image URLs to the <code>podd_symbol</code> field in your card definitions. The system 
                will prioritize PODD symbols when available and fall back to emojis for preview purposes.
            </div>
            """, unsafe_allow_html=True)
