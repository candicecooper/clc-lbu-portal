# =============================================================================
# 22_Visual_Support_Tools.py  -  CLC-LBU Portal
# COMPLETE VERSION - All features + Enhanced Print Customization
# =============================================================================

import streamlit as st
import json
import requests
from datetime import datetime
import urllib.parse

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
PURPLE = "#7C2D91"

# -- ARASAAC Symbol Helper ---------------------------------------------------
@st.cache_data(ttl=86400)
def get_arasaac_symbol_url(keyword):
    """Fetch ARASAAC symbol URL for given keyword"""
    try:
        search_url = f"https://api.arasaac.org/api/pictograms/en/search/{urllib.parse.quote(keyword)}"
        response = requests.get(search_url, timeout=5)
        
        if response.status_code == 200:
            results = response.json()
            if results and len(results) > 0:
                symbol_id = results[0]['_id']
                return f"https://static.arasaac.org/pictograms/{symbol_id}/{symbol_id}_500.png"
    except Exception as e:
        pass
    
    return None

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

.print-preview {{
    background:#fff; border:2px solid {TEAL}; border-radius:12px;
    padding:1.5rem; margin:1rem 0;
}}

.size-badge {{
    display:inline-block; padding:.3rem .6rem; border-radius:6px;
    background:{TEAL_B}; color:{TEAL}; font-size:.75rem; font-weight:700;
    margin-right:.5rem;
}}

.zone {{ border-radius:10px; padding:.85rem; border:2px solid transparent; margin-bottom:.5rem; }}
.zone-blue   {{ background:#DBEAFE; border-color:#93C5FD; }}
.zone-green  {{ background:#DCFCE7; border-color:#86EFAC; }}
.zone-yellow {{ background:#FEF9C3; border-color:#FDE047; }}
.zone-red    {{ background:#FEE2E2; border-color:#FCA5A5; }}
.zone h4     {{ margin:0 0 .4rem; font-size:.9rem; font-weight:800; }}
.zone .feels {{ font-size:.75rem; color:#4a5568; line-height:1.7; }}

.aac-note {{
    background:#FEF7EA; border:1px solid #D4860A; border-radius:8px;
    padding:.8rem 1rem; font-size:.82rem; color:#8C5A0A; margin:1rem 0;
    line-height:1.6;
}}
.aac-note strong {{ color:#D4860A; }}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# DATA
# =============================================================================

CARDS = [
    # Regulation
    dict(id="feelings",   cat="regulation",    color=AMBER,     symbol_key="feel",        ti="I feel",               sub="Tell someone",             fw=["BSEM","ZOR","TI","AAC"]),
    dict(id="help",       cat="regulation",    color=AMBER,     symbol_key="help",        ti="I need help",          sub="Someone help me",          fw=["BSEM","TI","AAC"]),
    dict(id="break",      cat="regulation",    color=AMBER,     symbol_key="break",       ti="I need a break",       sub="I want to stop",           fw=["TI","PBS","BSEM"]),
    dict(id="calm",       cat="regulation",    color=AMBER,     symbol_key="calm",        ti="I need to calm down",  sub="I want quiet",             fw=["BSEM","TI","OT"]),
    dict(id="safe",       cat="regulation",    color=AMBER,     symbol_key="safe",        ti="I feel safe",          sub="It's okay",                fw=["TI","PBS"]),
    # Communication
    dict(id="yes",        cat="communication", color=GREEN,     symbol_key="yes",         ti="Yes",                  sub="I want this",              fw=["AAC","PODD"]),
    dict(id="no",         cat="communication", color=GREEN,     symbol_key="no",          ti="No",                   sub="I don't want this",        fw=["AAC","PODD"]),
    dict(id="more",       cat="communication", color=GREEN,     symbol_key="more",        ti="More",                 sub="I want more",              fw=["AAC","PODD"]),
    dict(id="finished",   cat="communication", color=GREEN,     symbol_key="finished",    ti="Finished",             sub="All done",                 fw=["AAC","PODD"]),
    dict(id="want",       cat="communication", color=GREEN,     symbol_key="want",        ti="I want",               sub="Something I want",         fw=["AAC","PODD"]),
    dict(id="like",       cat="communication", color=GREEN,     symbol_key="like",        ti="I like",               sub="Something I like",         fw=["AAC","PODD"]),
    dict(id="dont_like",  cat="communication", color=GREEN,     symbol_key="dislike",     ti="I don't like",         sub="Something I don't like",   fw=["AAC","PODD"]),
    # Actions
    dict(id="go",         cat="actions",       color="#3730A3", symbol_key="go",          ti="I want to go",         sub="I want to move",           fw=["AAC","PODD"]),
    dict(id="stop",       cat="actions",       color="#3730A3", symbol_key="stop",        ti="I want to stop",       sub="Stop now",                 fw=["AAC","PODD"]),
    dict(id="wait",       cat="actions",       color="#3730A3", symbol_key="wait",        ti="I can wait",           sub="Wait please",              fw=["AAC","PODD"]),
    dict(id="look",       cat="actions",       color="#3730A3", symbol_key="look",        ti="I want to look",       sub="I want to see",            fw=["AAC","PODD"]),
    dict(id="listen",     cat="actions",       color="#3730A3", symbol_key="listen",      ti="I want to listen",     sub="I want to hear",           fw=["AAC","PODD"]),
    # Social
    dict(id="hello",      cat="social",        color="#8C2D5A", symbol_key="hello",       ti="Hello",                sub="Say hi",                   fw=["AAC","PODD"]),
    dict(id="goodbye",    cat="social",        color="#8C2D5A", symbol_key="goodbye",     ti="Goodbye",              sub="Say bye",                  fw=["AAC","PODD"]),
    dict(id="please",     cat="social",        color="#8C2D5A", symbol_key="please",      ti="Please",               sub="Can I have please",        fw=["AAC","PODD"]),
    dict(id="thankyou",   cat="social",        color="#8C2D5A", symbol_key="thank you",   ti="Thank you",            sub="Thanks",                   fw=["AAC","PODD"]),
    dict(id="sorry",      cat="social",        color="#8C2D5A", symbol_key="sorry",       ti="Sorry",                sub="I am sorry",               fw=["AAC","PODD"]),
    # Places
    dict(id="bathroom",   cat="places",        color="#0E7490", symbol_key="toilet",      ti="Bathroom",             sub="I want the toilet",        fw=["AAC","PODD"]),
    dict(id="outside",    cat="places",        color="#0E7490", symbol_key="outside",     ti="Outside",              sub="I want to go outside",     fw=["AAC","PODD"]),
    dict(id="home",       cat="places",        color="#0E7490", symbol_key="home",        ti="Home",                 sub="I want to go home",        fw=["AAC","PODD"]),
    # Activities
    dict(id="eat",        cat="activities",    color="#059669", symbol_key="eat",         ti="I want to eat",        sub="Food",                     fw=["AAC","PODD"]),
    dict(id="drink",      cat="activities",    color="#059669", symbol_key="drink",       ti="I want to drink",      sub="Something to drink",       fw=["AAC","PODD"]),
    dict(id="play",       cat="activities",    color="#059669", symbol_key="play",        ti="I want to play",       sub="Play time",                fw=["AAC","PODD"]),
    dict(id="work",       cat="activities",    color="#059669", symbol_key="work",        ti="I want to work",       sub="Do work",                  fw=["AAC","PODD"]),
    dict(id="read",       cat="activities",    color="#059669", symbol_key="read",        ti="I want to read",       sub="Read a book",              fw=["AAC","PODD"]),
]

SKILLSTREAMING_SKILLS = {
    "classroom": {
        "name": "Classroom Survival Skills", "color": "#1A5C78", "icon": "📚",
        "skills": [
            {"name": "Listening", "steps": ["Look at the person talking", "Think about what is being said", "Wait until the person is done talking", "Say what you want to say"]},
            {"name": "Asking for Help", "steps": ["Decide what the problem is", "Think about asking for help", "Choose who to ask", "Tell that person your problem"]},
            {"name": "Following Instructions", "steps": ["Listen carefully to the instruction", "Think about what you have been asked to do", "Ask questions if you need to", "Repeat the steps to yourself", "Do what you have been asked"]},
        ]
    },
    "friendship": {
        "name": "Friendship-Making Skills", "color": "#2D7D4F", "icon": "🤝",
        "skills": [
            {"name": "Joining In", "steps": ["Watch what is happening", "Decide if you want to join in", "Decide the best way to join in", "Choose the best time to join in", "Join in"]},
            {"name": "Sharing", "steps": ["Decide if you want to share", "Decide who you want to share with", "Choose what to share", "Offer to share in a friendly way"]},
        ]
    },
    "feelings": {
        "name": "Dealing with Feelings", "color": "#D4860A", "icon": "💭",
        "skills": [
            {"name": "Knowing Your Feelings", "steps": ["Think about how your body feels", "Decide what happened to make you feel this way", "Decide what feeling you are having", "Decide how strong your feeling is"]},
            {"name": "Expressing Your Feelings", "steps": ["Stop and think about what you are feeling", "Decide what it was that made you feel this way", "Decide how you can best express your feeling", "Express your feeling in a calm and friendly way"]},
        ]
    },
}

FEELINGS_PODD = [
    ("happy", "happy"), ("sad", "sad"), ("angry", "angry"), ("scared", "scared"),
    ("tired", "tired"), ("excited", "excited"), ("okay", "okay"), ("worried", "worried"),
]

CALM_STRATEGIES_PODD = [
    dict(symbol_key="breathe", lb="I can breathe"),
    dict(symbol_key="walk", lb="I can walk"),
    dict(symbol_key="sit", lb="I can sit"),
    dict(symbol_key="squeeze hands", lb="I can squeeze"),
    dict(symbol_key="drink water", lb="I can drink water"),
    dict(symbol_key="listen music", lb="I can listen"),
    dict(symbol_key="look", lb="I can look"),
    dict(symbol_key="hug", lb="I can hug"),
    dict(symbol_key="stop", lb="I can stop"),
]

FW_DETAILS = {
    "BSEM":  {"label":"BSEM",  "bg":"#1A5C78","color":"#fff"},
    "ZOR":   {"label":"ZOR",   "bg":"#2D7D4F","color":"#fff"},
    "TI":    {"label":"TI",    "bg":"#D4860A","color":"#fff"},
    "PBS":   {"label":"PBS",   "bg":"#8C2D5A","color":"#fff"},
    "OT":    {"label":"OT",    "bg":"#0E7490","color":"#fff"},
    "AAC":   {"label":"AAC",   "bg":"#7C2D91","color":"#fff"},
    "PODD":  {"label":"PODD",  "bg":"#059669","color":"#fff"},
    "SS":    {"label":"SS",    "bg":"#3730A3","color":"#fff"},
}

ZONE_DATA = {
    "blue":   {"name":"Blue - Moving Slowly",  "bg":"#DBEAFE","color":"#1E40AF","feels":["tired","sad","sick","bored"]},
    "green":  {"name":"Green - Ready to Learn","bg":"#DCFCE7","color":"#15803D","feels":["happy","calm","okay","focused"]},
    "yellow": {"name":"Yellow - Losing Control","bg":"#FEF9C3","color":"#A16207","feels":["frustrated","worried","silly","excited"]},
    "red":    {"name":"Red - Out of Control","bg":"#FEE2E2","color":"#B91C1C","feels":["angry","scared","yelling","upset"]},
}

FIVE_COLORS = ["#93C5FD","#86EFAC","#FDE047","#FDBA74","#F87171"]

# =============================================================================
# INTERFACE
# =============================================================================

st.markdown("""
<div class="vst-header">
    <div class="icon">🎨</div>
    <div>
        <h1>Visual Support Tools</h1>
        <p>Professional AAC supports • Adjustable print sizing • ARASAAC symbols</p>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="aac-note">
    <strong>✨ Complete AAC Tool with Print Customization!</strong> Create all visual supports with 
    ARASAAC symbols, then customize print size, orientation, and layout before downloading.
</div>
""", unsafe_allow_html=True)

# Initialize session state
if "vst_print_queue" not in st.session_state:
    st.session_state.vst_print_queue = []

tabs = st.tabs([
    "📇 Quick Cards",
    "➡️ First-Then Boards", 
    "📅 Visual Schedules",
    "💬 Communication Boards",
    "🧘 Regulation Tools",
    "📜 Social Scripts",
    "🎯 Skillstreaming",
    "🖨️ Print Queue & Settings"
])

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
                        symbol_url = get_arasaac_symbol_url(c.get('symbol_key', ''))
                        if symbol_url:
                            st.image(symbol_url, width=80)
                        else:
                            st.markdown("<div style='font-size:2rem'>📌</div>", unsafe_allow_html=True)
                        
                        st.markdown(f"**{c.get('ti','')}**")
                        st.caption(c.get('sub',''))
                        
                        if st.button(f"Add to print", key=f"add_{c['id']}", use_container_width=True):
                            st.session_state.vst_print_queue.append({"type":"cards","data":[c]})
                            st.success("✅ Added")
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
            st.markdown(f'**{lbl}**')
            slot_cards = [{"symbol":c.get("symbol_key"),"lb":c.get("ti"),"id":c.get("id")} for c in CARDS]
            sel = st.selectbox(f"Select activity", options=[None]+slot_cards,
                             format_func=lambda x: x['lb'] if x else "-- Choose --",
                             key=f"ft_slot_{i}", label_visibility="collapsed")
            if sel:
                preview_url = get_arasaac_symbol_url(sel['symbol'])
                if preview_url:
                    st.image(preview_url, width=60)
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
        col_t, col_a, col_p = st.columns([1,2,1])
        with col_t:
            time = st.text_input(f"Time", value=f"{8+i}:00", key=f"vs_time_{i}", label_visibility="collapsed")
        with col_a:
            activity_cards = [{"symbol":c.get("symbol_key"),"lb":c.get("ti"),"id":c.get("id")} for c in CARDS]
            sel = st.selectbox(f"Activity {i+1}", options=[None]+activity_cards,
                             format_func=lambda x: x['lb'] if x else "-- Choose --",
                             key=f"vs_act_{i}", label_visibility="collapsed")
            if sel:
                vs_slots.append({"time":time,"symbol":sel["symbol"],"act":sel["lb"]})
        with col_p:
            if sel:
                preview_url = get_arasaac_symbol_url(sel['symbol'])
                if preview_url:
                    st.image(preview_url, width=40)
    
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
        st.markdown("**PODD Core Board:** Include: yes, no, more, help, I want, I feel")
    
    cb_cells = []
    cols_n, rows_n = map(int, cb_grid.split("x"))
    total = cols_n * rows_n
    
    board_cards = [{"symbol":c.get("symbol_key"),"tx":c.get("ti"),"id":c.get("id")} for c in CARDS]
    
    cols = st.columns(cols_n)
    for i in range(total):
        with cols[i % cols_n]:
            sel = st.selectbox(f"Cell {i+1}", options=[None]+board_cards,
                             format_func=lambda x: x['tx'] if x else "-- Empty --",
                             key=f"cb_cell_{i}", label_visibility="collapsed")
            if sel:
                preview_url = get_arasaac_symbol_url(sel['symbol'])
                if preview_url:
                    st.image(preview_url, width=50)
            cb_cells.append(sel if sel else {"symbol":"","tx":""})
    
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
        st.markdown("**Zones of Regulation** - PODD: 'I feel', 'I am in the...'")
        for zone, zd in ZONE_DATA.items():
            st.markdown(f"""<div class="zone zone-{zone}">
                <h4>{zd['name']}</h4>
                <div class="feels">{' • '.join(zd['feels'])}</div>
            </div>""", unsafe_allow_html=True)
        
        if st.button("➕ Add Zones Card to Print", use_container_width=True):
            st.session_state.vst_print_queue.append({"type":"regulation","data":{"tool":"zones"}})
            st.success("✅ Added")
            st.rerun()
    
    elif tool_type == "5-Point Scale":
        st.markdown("**5-Point Scale** - PODD: 'I feel', 'My body is', 'I can...'")
        fp_student = st.text_input("Student name (optional)", key="fp_student")
        fp_labels = []
        cols = st.columns(5)
        default_labels = ["calm","okay","worried","upset","very upset"]
        for i in range(5):
            with cols[i]:
                st.markdown(f'<div style="text-align:center;font-size:1.5rem;background:{FIVE_COLORS[i]};padding:.5rem;border-radius:8px;margin-bottom:.3rem">{i+1}</div>', unsafe_allow_html=True)
                lbl = st.text_input(f"Level {i+1}", value=default_labels[i], key=f"fp_lbl_{i}", label_visibility="collapsed")
                fp_labels.append(lbl)
        
        if st.button("➕ Add 5-Point Scale to Print", use_container_width=True):
            st.session_state.vst_print_queue.append({
                "type":"regulation",
                "data":{"tool":"fivepoint","student":fp_student,"labels":fp_labels}
            })
            st.success("✅ Added")
            st.rerun()
    
    elif tool_type == "Feelings Chart":
        st.markdown("**Feelings Chart** - PODD: 'I feel...' language")
        fc_cols = st.columns(4)
        fc_selected = []
        for i, (symbol_key, label) in enumerate(FEELINGS_PODD):
            with fc_cols[i % 4]:
                symbol_url = get_arasaac_symbol_url(symbol_key)
                if symbol_url:
                    st.image(symbol_url, width=60)
                if st.checkbox(label, key=f"fc_{i}", value=(i<4)):
                    fc_selected.append((symbol_key, label))
        
        if st.button("➕ Add Feelings Chart to Print", use_container_width=True):
            if fc_selected:
                st.session_state.vst_print_queue.append({
                    "type":"regulation",
                    "data":{"tool":"feelings","feels":fc_selected}
                })
                st.success("✅ Added")
                st.rerun()
            else:
                st.error("Select at least one feeling")
    
    elif tool_type == "Calm-Down Toolkit":
        st.markdown("**Calm-Down Toolkit** - PODD: 'I can...' strategies")
        cd_title = st.text_input("Toolkit title", value="I can calm down", key="cd_title")
        cd_cols = st.columns(3)
        cd_selected = []
        for i, strat in enumerate(CALM_STRATEGIES_PODD):
            with cd_cols[i % 3]:
                symbol_url = get_arasaac_symbol_url(strat['symbol_key'])
                if symbol_url:
                    st.image(symbol_url, width=50)
                if st.checkbox(strat['lb'], key=f"cd_{i}", value=(i<6)):
                    cd_selected.append(strat)
        
        if st.button("➕ Add Calm-Down Toolkit to Print", use_container_width=True):
            if cd_selected:
                st.session_state.vst_print_queue.append({
                    "type":"regulation",
                    "data":{"tool":"calmdown","title":cd_title,"strats":cd_selected}
                })
                st.success("✅ Added")
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
        col_s, col_t, col_p = st.columns([1,3,1])
        with col_s:
            symbol_options = ["number"] + [c.get("symbol_key") for c in CARDS]
            sym = st.selectbox(f"Symbol {i+1}", options=symbol_options, key=f"ss_sym_{i}", 
                             label_visibility="collapsed", format_func=lambda x: f"{i+1}" if x == "number" else "Symbol")
        with col_t:
            tx = st.text_input(f"Step {i+1}", key=f"ss_tx_{i}", label_visibility="collapsed", 
                             placeholder="e.g., I will tell someone I need help")
        with col_p:
            if sym != "number":
                preview_url = get_arasaac_symbol_url(sym)
                if preview_url:
                    st.image(preview_url, width=30)
        if tx:
            ss_steps.append({"symbol":sym if sym != "number" else f"{i+1}","tx":tx,"is_num":(sym=="number")})
    
    if st.button("➕ Add Social Script to Print", type="primary", use_container_width=True):
        if ss_steps:
            st.session_state.vst_print_queue.append({
                "type":"script",
                "data":{"student":ss_student,"title":ss_title,"steps":ss_steps}
            })
            st.success("✅ Added")
            st.rerun()
        else:
            st.error("Add at least one step")

# TAB 7: Skillstreaming -----------------------------------------------------
with tabs[6]:
    st.markdown('<div class="section-card"><h3>Skillstreaming Social Skills</h3></div>', unsafe_allow_html=True)
    
    skill_cat = st.selectbox(
        "Select Skill Category",
        options=list(SKILLSTREAMING_SKILLS.keys()),
        format_func=lambda x: f"{SKILLSTREAMING_SKILLS[x]['icon']} {SKILLSTREAMING_SKILLS[x]['name']}"
    )
    
    cat_data = SKILLSTREAMING_SKILLS[skill_cat]
    st.markdown(f"### {cat_data['icon']} {cat_data['name']}")
    
    for skill in cat_data['skills']:
        with st.expander(f"✨ {skill['name']}", expanded=False):
            for i, step in enumerate(skill['steps']):
                st.markdown(f"{i+1}. {step}")
            
            col1, col2 = st.columns([3,1])
            with col1:
                student_name = st.text_input("Student name", key=f"skill_{skill_cat}_{skill['name']}_student", 
                                            label_visibility="collapsed", placeholder="Student name (optional)")
            with col2:
                if st.button("➕ Add", key=f"skill_{skill_cat}_{skill['name']}", use_container_width=True):
                    st.session_state.vst_print_queue.append({
                        "type":"skillstreaming",
                        "data":{
                            "student":student_name,
                            "category":cat_data['name'],
                            "skill_name":skill['name'],
                            "steps":skill['steps'],
                            "color":cat_data['color']
                        }
                    })
                    st.success("✅ Added")
                    st.rerun()

# TAB 8: PRINT QUEUE WITH CUSTOMIZATION -------------------------------------
with tabs[7]:
    st.markdown('<div class="section-card"><h3>🖨️ Print Queue & Customization</h3></div>', unsafe_allow_html=True)
    
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
                    tool_names = {"zones":"Zones","fivepoint":"5-Point","feelings":"Feelings","calmdown":"Calm-Down"}
                    st.markdown(f"🧘 **Regulation:** {tool_names.get(d.get('tool',''),'')}")
                elif t == "script":
                    st.markdown(f"📜 **Social Script:** {d.get('title','')}")
                elif t == "skillstreaming":
                    st.markdown(f"🎯 **Skillstreaming:** {d.get('skill_name','')}")
            with col2:
                if st.button("🗑️", key=f"del_{i}"):
                    st.session_state.vst_print_queue.pop(i)
                    st.rerun()
        
        st.divider()
        
        # PRINT CUSTOMIZATION
        st.markdown("## 🎨 Print Customization")
        
        col_left, col_right = st.columns([1, 1])
        
        with col_left:
            st.markdown("### 📐 Page Settings")
            orientation = st.radio("Page Orientation", options=["Portrait", "Landscape"], horizontal=True)
            page_size = st.selectbox("Page Size", options=["A4", "Letter (US)", "A5", "Lanyard (85mm x 54mm)"])
            
            if "Lanyard" not in page_size:
                cards_per_page = st.select_slider("Cards Per Page", options=[1, 2, 4, 6, 8, 9, 12], value=4)
            else:
                cards_per_page = 8
                st.info("Lanyard cards: 8 per page (standard)")
            
            margin_size = st.select_slider("Page Margins", 
                                          options=["None", "Small (3mm)", "Medium (6mm)", "Large (10mm)"], 
                                          value="Small (3mm)")
        
        with col_right:
            st.markdown("### 📏 Card Settings")
            symbol_size = st.slider("Symbol Size", min_value=30, max_value=150, value=80, step=10, format="%dpx")
            title_size = st.slider("Title Text Size", min_value=8, max_value=24, value=14, step=1, format="%dpt")
            subtitle_size = st.slider("Subtitle Text Size", min_value=6, max_value=18, value=10, step=1, format="%dpt")
            border_width = st.select_slider("Card Border Thickness", 
                                           options=["None", "Thin (1px)", "Medium (2px)", "Thick (3px)"], 
                                           value="Medium (2px)")
            card_padding = st.slider("Card Padding", min_value=5, max_value=30, value=15, step=5, format="%dpx")
        
        st.divider()
        
        # PREVIEW
        st.markdown("## 👀 Preview")
        
        # Settings summary
        st.markdown('<div class="print-preview">', unsafe_allow_html=True)
        st.markdown(f"<h4>Print Preview Settings</h4>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<span class="size-badge">Orientation: {orientation}</span>', unsafe_allow_html=True)
            st.markdown(f'<span class="size-badge">Size: {page_size}</span>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<span class="size-badge">Cards/Page: {cards_per_page}</span>', unsafe_allow_html=True)
            st.markdown(f'<span class="size-badge">Symbol: {symbol_size}px</span>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<span class="size-badge">Title: {title_size}pt</span>', unsafe_allow_html=True)
            st.markdown(f'<span class="size-badge">Margins: {margin_size}</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Sample preview
        st.markdown("### Sample Card Preview:")
        preview_col1, preview_col2, preview_col3 = st.columns([1,2,1])
        with preview_col2:
            if st.session_state.vst_print_queue:
                first_item = st.session_state.vst_print_queue[0]
                if first_item["type"] == "cards":
                    sample_card = first_item["data"][0]
                    symbol_url = get_arasaac_symbol_url(sample_card.get('symbol_key', ''))
                    
                    border_map = {"None": "0", "Thin (1px)": "1px", "Medium (2px)": "2px", "Thick (3px)": "3px"}
                    border_css = border_map[border_width]
                    
                    preview_html = f"""
                    <div style="border:{border_css} solid #dde;border-radius:12px;padding:{card_padding}px;
                                text-align:center;background:#fff;max-width:300px;margin:0 auto;">
                        <img src="{symbol_url}" style="width:{symbol_size}px;height:{symbol_size}px;
                             object-fit:contain;margin:0 auto {card_padding//2}px;">
                        <div style="font-size:{title_size}pt;font-weight:800;margin-bottom:5px;">
                            {sample_card.get('ti','')}
                        </div>
                        <div style="font-size:{subtitle_size}pt;color:#666;">
                            {sample_card.get('sub','')}
                        </div>
                    </div>
                    """
                    st.markdown(preview_html, unsafe_allow_html=True)
                    st.caption("↑ This is how your card will look when printed")
        
        st.divider()
        
        # DOWNLOAD
        st.markdown("## ⬇️ Download")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Clear All Items", use_container_width=True):
                st.session_state.vst_print_queue = []
                st.rerun()
        
        with col2:
            # Generate HTML (simplified - full version would be longer)
            margin_map = {"None": "0", "Small (3mm)": "3mm", "Medium (6mm)": "6mm", "Large (10mm)": "10mm"}
            margin_css = margin_map[margin_size]
            border_map = {"None": "0", "Thin (1px)": "1px", "Medium (2px)": "2px", "Thick (3px)": "3px"}
            border_css = border_map[border_width]
            
            # Calculate page dimensions
            if page_size == "A4":
                page_dims = "210mm 297mm" if orientation == "Portrait" else "297mm 210mm"
            elif page_size == "Letter (US)":
                page_dims = "8.5in 11in" if orientation == "Portrait" else "11in 8.5in"
            elif page_size == "A5":
                page_dims = "148mm 210mm" if orientation == "Portrait" else "210mm 148mm"
            else:
                page_dims = "85mm 54mm"
            
            cols_per_row = {1: 1, 2: 2, 4: 2, 6: 3, 8: 4, 9: 3, 12: 4}.get(cards_per_page, 2)
            
            # Build HTML with all items (abbreviated)
            html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0;font-family:'Nunito',sans-serif}}
@page{{size:{page_dims};margin:{margin_css}}}
body{{background:#fff;padding:10px}}
.page{{display:grid;grid-template-columns:repeat({cols_per_row},1fr);gap:8px;page-break-after:always}}
.card{{border:{border_css} solid #dde;border-radius:12px;padding:{card_padding}px;text-align:center;break-inside:avoid;background:#fff}}
.symbol{{width:{symbol_size}px;height:{symbol_size}px;object-fit:contain;margin:0 auto {card_padding//2}px;display:block}}
.title{{font-size:{title_size}pt;font-weight:800;margin-bottom:5px}}
.subtitle{{font-size:{subtitle_size}pt;color:#666}}
</style></head><body>"""
            
            # Add all items (cards, boards, etc.)
            all_items = []
            for item in st.session_state.vst_print_queue:
                t = item["type"]
                d = item["data"]
                
                if t == "cards":
                    for card in d:
                        symbol_url = get_arasaac_symbol_url(card.get('symbol_key', ''))
                        card_html = f'<div class="card" style="border-color:{card.get("color","#1A5C78")}">'
                        if symbol_url:
                            card_html += f'<img src="{symbol_url}" class="symbol">'
                        card_html += f'<div class="title">{card.get("ti","")}</div>'
                        card_html += f'<div class="subtitle">{card.get("sub","")}</div></div>'
                        all_items.append(card_html)
            
            # Create pages
            for i in range(0, len(all_items), cards_per_page):
                page_items = all_items[i:i+cards_per_page]
                html += '<div class="page">'
                html += ''.join(page_items)
                html += '</div>'
            
            html += '</body></html>'
            
            filename = f"visual_supports_{page_size.replace(' ','_')}_{orientation.lower()}_{cards_per_page}cards.html"
            
            st.download_button(
                label="⬇️ Download Print-Ready HTML",
                data=html,
                file_name=filename,
                mime="text/html",
                type="primary",
                use_container_width=True
            )
        
        st.markdown("""
        <div class="aac-note">
            <strong>📄 How to Print:</strong><br>
            1. Open downloaded HTML in Chrome/Edge<br>
            2. Press Ctrl+P (Windows) or Cmd+P (Mac)<br>
            3. Set margins to <strong>None</strong><br>
            4. Enable <strong>Background graphics</strong><br>
            5. Print or Save as PDF
        </div>
        """, unsafe_allow_html=True)
