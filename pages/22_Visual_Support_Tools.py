# =============================================================================
# 22_Visual_Support_Tools.py  -  CLC-LBU Portal
# ULTIMATE VERSION - All resource types + Individual settings + Custom cards + Search
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

.queue-item {{
    background:#fff; border:2px solid #dde; border-radius:8px;
    padding:.8rem 1rem; margin-bottom:.6rem; cursor:pointer;
    transition:all 0.2s;
}}
.queue-item:hover {{
    border-color:{TEAL}; box-shadow:0 2px 6px rgba(26,92,120,.2);
}}
.queue-item.selected {{
    border-color:{TEAL}; background:{TEAL_B};
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

.custom-badge {{
    display:inline-block; padding:.2rem .5rem; border-radius:12px;
    background:#7C2D91; color:#fff; font-size:.65rem; font-weight:700;
    margin-left:.3rem;
}}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# DATA
# =============================================================================

DEFAULT_CARDS = [
    # Regulation
    dict(id="feelings",   cat="regulation",    color=AMBER,     symbol_key="feel",        ti="I feel",               sub="Tell someone",             fw=["BSEM","ZOR","TI","AAC"], custom=False),
    dict(id="help",       cat="regulation",    color=AMBER,     symbol_key="help",        ti="I need help",          sub="Someone help me",          fw=["BSEM","TI","AAC"], custom=False),
    dict(id="break",      cat="regulation",    color=AMBER,     symbol_key="break",       ti="I need a break",       sub="I want to stop",           fw=["TI","PBS","BSEM"], custom=False),
    dict(id="calm",       cat="regulation",    color=AMBER,     symbol_key="calm",        ti="I need to calm down",  sub="I want quiet",             fw=["BSEM","TI","OT"], custom=False),
    dict(id="safe",       cat="regulation",    color=AMBER,     symbol_key="safe",        ti="I feel safe",          sub="It's okay",                fw=["TI","PBS"], custom=False),
    # Communication
    dict(id="yes",        cat="communication", color=GREEN,     symbol_key="yes",         ti="Yes",                  sub="I want this",              fw=["AAC","PODD"], custom=False),
    dict(id="no",         cat="communication", color=GREEN,     symbol_key="no",          ti="No",                   sub="I don't want this",        fw=["AAC","PODD"], custom=False),
    dict(id="more",       cat="communication", color=GREEN,     symbol_key="more",        ti="More",                 sub="I want more",              fw=["AAC","PODD"], custom=False),
    dict(id="finished",   cat="communication", color=GREEN,     symbol_key="finished",    ti="Finished",             sub="All done",                 fw=["AAC","PODD"], custom=False),
    dict(id="want",       cat="communication", color=GREEN,     symbol_key="want",        ti="I want",               sub="Something I want",         fw=["AAC","PODD"], custom=False),
    dict(id="like",       cat="communication", color=GREEN,     symbol_key="like",        ti="I like",               sub="Something I like",         fw=["AAC","PODD"], custom=False),
    dict(id="dont_like",  cat="communication", color=GREEN,     symbol_key="dislike",     ti="I don't like",         sub="Something I don't like",   fw=["AAC","PODD"], custom=False),
    # Actions
    dict(id="go",         cat="actions",       color="#3730A3", symbol_key="go",          ti="I want to go",         sub="I want to move",           fw=["AAC","PODD"], custom=False),
    dict(id="stop",       cat="actions",       color="#3730A3", symbol_key="stop",        ti="I want to stop",       sub="Stop now",                 fw=["AAC","PODD"], custom=False),
    dict(id="wait",       cat="actions",       color="#3730A3", symbol_key="wait",        ti="I can wait",           sub="Wait please",              fw=["AAC","PODD"], custom=False),
    dict(id="look",       cat="actions",       color="#3730A3", symbol_key="look",        ti="I want to look",       sub="I want to see",            fw=["AAC","PODD"], custom=False),
    dict(id="listen",     cat="actions",       color="#3730A3", symbol_key="listen",      ti="I want to listen",     sub="I want to hear",           fw=["AAC","PODD"], custom=False),
    # Social
    dict(id="hello",      cat="social",        color="#8C2D5A", symbol_key="hello",       ti="Hello",                sub="Say hi",                   fw=["AAC","PODD"], custom=False),
    dict(id="goodbye",    cat="social",        color="#8C2D5A", symbol_key="goodbye",     ti="Goodbye",              sub="Say bye",                  fw=["AAC","PODD"], custom=False),
    dict(id="please",     cat="social",        color="#8C2D5A", symbol_key="please",      ti="Please",               sub="Can I have please",        fw=["AAC","PODD"], custom=False),
    dict(id="thankyou",   cat="social",        color="#8C2D5A", symbol_key="thank you",   ti="Thank you",            sub="Thanks",                   fw=["AAC","PODD"], custom=False),
    dict(id="sorry",      cat="social",        color="#8C2D5A", symbol_key="sorry",       ti="Sorry",                sub="I am sorry",               fw=["AAC","PODD"], custom=False),
    # Places
    dict(id="bathroom",   cat="places",        color="#0E7490", symbol_key="toilet",      ti="Bathroom",             sub="I want the toilet",        fw=["AAC","PODD"], custom=False),
    dict(id="outside",    cat="places",        color="#0E7490", symbol_key="outside",     ti="Outside",              sub="I want to go outside",     fw=["AAC","PODD"], custom=False),
    dict(id="home",       cat="places",        color="#0E7490", symbol_key="home",        ti="Home",                 sub="I want to go home",        fw=["AAC","PODD"], custom=False),
    # Activities
    dict(id="eat",        cat="activities",    color="#059669", symbol_key="eat",         ti="I want to eat",        sub="Food",                     fw=["AAC","PODD"], custom=False),
    dict(id="drink",      cat="activities",    color="#059669", symbol_key="drink",       ti="I want to drink",      sub="Something to drink",       fw=["AAC","PODD"], custom=False),
    dict(id="play",       cat="activities",    color="#059669", symbol_key="play",        ti="I want to play",       sub="Play time",                fw=["AAC","PODD"], custom=False),
    dict(id="work",       cat="activities",    color="#059669", symbol_key="work",        ti="I want to work",       sub="Do work",                  fw=["AAC","PODD"], custom=False),
    dict(id="read",       cat="activities",    color="#059669", symbol_key="read",        ti="I want to read",       sub="Read a book",              fw=["AAC","PODD"], custom=False),
]

SKILLSTREAMING_SKILLS = {
    "classroom": {
        "name": "Classroom Survival Skills", "color": "#1A5C78", "icon": "📚",
        "skills": [
            {"name": "Listening", "steps": ["Look at the person talking", "Think about what is being said", "Wait until the person is done talking", "Say what you want to say"]},
            {"name": "Asking for Help", "steps": ["Decide what the problem is", "Think about asking for help", "Choose who to ask", "Tell that person your problem"]},
        ]
    },
    "friendship": {
        "name": "Friendship-Making Skills", "color": "#2D7D4F", "icon": "🤝",
        "skills": [
            {"name": "Joining In", "steps": ["Watch what is happening", "Decide if you want to join in", "Decide the best way to join in", "Choose the best time to join in", "Join in"]},
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
# INITIALIZE SESSION STATE
# =============================================================================

if "vst_print_queue" not in st.session_state:
    st.session_state.vst_print_queue = []

if "vst_custom_cards" not in st.session_state:
    st.session_state.vst_custom_cards = []

if "vst_selected_item_index" not in st.session_state:
    st.session_state.vst_selected_item_index = None

if "vst_search_query" not in st.session_state:
    st.session_state.vst_search_query = ""

# Combine default and custom cards
ALL_CARDS = DEFAULT_CARDS + st.session_state.vst_custom_cards

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def add_to_queue_with_defaults(item_dict):
    """Add item to queue with default print settings"""
    item_dict['print_settings'] = {
        'orientation': 'Portrait',
        'page_size': 'A4',
        'cards_per_page': 4,
        'symbol_size': 80,
        'title_size': 14,
        'subtitle_size': 10,
        'card_padding': 15
    }
    st.session_state.vst_print_queue.append(item_dict)

# =============================================================================
# INTERFACE
# =============================================================================

st.markdown("""
<div class="vst-header">
    <div class="icon">🎨</div>
    <div>
        <h1>Visual Support Tools - Complete</h1>
        <p>All resources • Individual settings • Custom cards • Search & filter</p>
    </div>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs([
    "📇 Card Library",
    "➕ Create Custom",
    "➡️ First-Then",
    "📅 Schedules",
    "💬 Comm Boards",
    "🧘 Regulation",
    "📜 Scripts",
    "🎯 Skillstreaming",
    "🖨️ Print Queue"
])

# TAB 1: Card Library with Search -----------------------------------------
with tabs[0]:
    st.markdown('<div class="section-card"><h3>Card Library with Search</h3></div>', unsafe_allow_html=True)
    
    # Search and filter
    col_search, col_cat, col_fw = st.columns([2, 1, 1])
    
    with col_search:
        search_query = st.text_input("🔍 Search cards", 
                                     value=st.session_state.vst_search_query,
                                     placeholder="Type to search...",
                                     key="search_input")
        st.session_state.vst_search_query = search_query
    
    with col_cat:
        cat_filter = st.selectbox("Filter by category", 
                                 options=["All"] + ["regulation","communication","actions","social","places","activities"])
    
    with col_fw:
        fw_filter = st.selectbox("Filter by framework",
                                options=["All"] + list(FW_DETAILS.keys()))
    
    # Filter cards
    filtered_cards = ALL_CARDS
    
    if search_query:
        filtered_cards = [c for c in filtered_cards 
                         if search_query.lower() in c.get('ti','').lower() 
                         or search_query.lower() in c.get('sub','').lower()
                         or search_query.lower() in c.get('symbol_key','').lower()]
    
    if cat_filter != "All":
        filtered_cards = [c for c in filtered_cards if c.get('cat') == cat_filter]
    
    if fw_filter != "All":
        filtered_cards = [c for c in filtered_cards if fw_filter in c.get('fw', [])]
    
    st.markdown(f"**{len(filtered_cards)} cards found**")
    
    if filtered_cards:
        cols = st.columns(4)
        for i, c in enumerate(filtered_cards):
            with cols[i % 4]:
                symbol_url = get_arasaac_symbol_url(c.get('symbol_key', ''))
                if symbol_url:
                    st.image(symbol_url, width=80)
                else:
                    st.markdown("<div style='font-size:2rem'>📌</div>", unsafe_allow_html=True)
                
                title_html = f"**{c.get('ti','')}**"
                if c.get('custom'):
                    title_html += '<span class="custom-badge">CUSTOM</span>'
                st.markdown(title_html, unsafe_allow_html=True)
                st.caption(c.get('sub',''))
                
                col_add, col_del = st.columns([3,1])
                with col_add:
                    if st.button(f"Add", key=f"add_{c['id']}_{i}", use_container_width=True):
                        add_to_queue_with_defaults({"type":"cards","data":[c]})
                        st.success("✅")
                        st.rerun()
                
                with col_del:
                    if c.get('custom'):
                        if st.button("🗑️", key=f"del_custom_{c['id']}_{i}"):
                            st.session_state.vst_custom_cards = [x for x in st.session_state.vst_custom_cards if x['id'] != c['id']]
                            st.success("Deleted")
                            st.rerun()
    else:
        st.info("No cards match your search/filters")

# TAB 2: Create Custom Card ----------------------------------------------
with tabs[1]:
    st.markdown('<div class="section-card"><h3>Create Custom Card</h3></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        custom_title = st.text_input("Card Title", placeholder="e.g., I need a drink", key="custom_title")
        custom_subtitle = st.text_input("Card Subtitle", placeholder="e.g., I want water", key="custom_subtitle")
        custom_symbol = st.text_input("Symbol Keyword", placeholder="e.g., water", key="custom_symbol")
        custom_category = st.selectbox("Category", options=["regulation","communication","actions","social","places","activities"], key="custom_category")
    
    with col2:
        custom_color = st.color_picker("Card Color", value=TEAL, key="custom_color")
        custom_frameworks = st.multiselect("Frameworks", options=list(FW_DETAILS.keys()), default=["AAC"], key="custom_frameworks")
        
        st.markdown("**Preview:**")
        if custom_symbol:
            preview_symbol_url = get_arasaac_symbol_url(custom_symbol)
            if preview_symbol_url:
                st.image(preview_symbol_url, width=100)
            else:
                st.warning("No symbol found")
    
    if st.button("➕ Add to Library", type="primary", use_container_width=True):
        if custom_title and custom_symbol:
            new_card = {
                'id': f"custom_{len(st.session_state.vst_custom_cards)}_{datetime.now().strftime('%H%M%S')}",
                'cat': custom_category,
                'color': custom_color,
                'symbol_key': custom_symbol,
                'ti': custom_title,
                'sub': custom_subtitle,
                'fw': custom_frameworks,
                'custom': True
            }
            st.session_state.vst_custom_cards.append(new_card)
            st.success(f"✅ Added '{custom_title}'! Go to Card Library to use it.")
            st.rerun()
        else:
            st.error("Enter title and symbol keyword")

# TAB 3: First-Then Boards ---------------------------------------------------
with tabs[2]:
    st.markdown('<div class="section-card"><h3>Build First-Then Board</h3></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        ft_student = st.text_input("Student name (optional)", key="ft_student")
        ft_title = st.text_input("Board title", value="First-Then", key="ft_title")
        ft_steps = st.radio("Number of steps", [2,3,4], horizontal=True, key="ft_steps")
    with col2:
        st.markdown("**PODD Tip:** Use 'I will...', 'I can...'")
    
    ft_labels = ["FIRST","THEN","NEXT","LAST"][:ft_steps]
    ft_slots = []
    
    cols = st.columns(ft_steps)
    for i, lbl in enumerate(ft_labels):
        with cols[i]:
            st.markdown(f'**{lbl}**')
            slot_cards = [{"symbol":c.get("symbol_key"),"lb":c.get("ti"),"id":c.get("id")} for c in ALL_CARDS]
            sel = st.selectbox(f"Activity", options=[None]+slot_cards,
                             format_func=lambda x: x['lb'] if x else "-- Choose --",
                             key=f"ft_slot_{i}", label_visibility="collapsed")
            if sel:
                preview_url = get_arasaac_symbol_url(sel['symbol'])
                if preview_url:
                    st.image(preview_url, width=60)
            ft_slots.append(sel)
    
    if st.button("➕ Add to Queue", type="primary", use_container_width=True):
        if all(s is not None for s in ft_slots):
            add_to_queue_with_defaults({
                "type":"firstthen",
                "data":{"student":ft_student,"title":ft_title,"labels":ft_labels,"slots":ft_slots}
            })
            st.success("✅ Added")
            st.rerun()
        else:
            st.error("Fill all slots")

# TAB 4: Visual Schedules ----------------------------------------------------
with tabs[3]:
    st.markdown('<div class="section-card"><h3>Build Visual Schedule</h3></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2,3])
    with col1:
        vs_student = st.text_input("Student name (optional)", key="vs_student")
        vs_title = st.text_input("Schedule title", value="My Schedule", key="vs_title")
        vs_slots_n = st.number_input("Activities", min_value=3, max_value=12, value=6, key="vs_slots_n")
    with col2:
        st.markdown("**PODD:** Use 'I will...', 'Time to...'")
    
    vs_slots = []
    for i in range(vs_slots_n):
        col_t, col_a, col_p = st.columns([1,2,1])
        with col_t:
            time = st.text_input(f"Time", value=f"{8+i}:00", key=f"vs_time_{i}", label_visibility="collapsed")
        with col_a:
            activity_cards = [{"symbol":c.get("symbol_key"),"lb":c.get("ti"),"id":c.get("id")} for c in ALL_CARDS]
            sel = st.selectbox(f"Activity", options=[None]+activity_cards,
                             format_func=lambda x: x['lb'] if x else "-- Choose --",
                             key=f"vs_act_{i}", label_visibility="collapsed")
            if sel:
                vs_slots.append({"time":time,"symbol":sel["symbol"],"act":sel["lb"]})
        with col_p:
            if sel:
                preview_url = get_arasaac_symbol_url(sel['symbol'])
                if preview_url:
                    st.image(preview_url, width=40)
    
    if st.button("➕ Add to Queue", type="primary", use_container_width=True):
        if vs_slots:
            add_to_queue_with_defaults({
                "type":"schedule",
                "data":{"student":vs_student,"title":vs_title,"slots":vs_slots}
            })
            st.success("✅ Added")
            st.rerun()
        else:
            st.error("Add activities")

# TAB 5: Communication Boards ------------------------------------------------
with tabs[4]:
    st.markdown('<div class="section-card"><h3>Build Communication Board</h3></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2,3])
    with col1:
        cb_title = st.text_input("Board title", value="I want to tell you", key="cb_title")
        cb_grid = st.selectbox("Grid size", ["2x2","2x3","3x3","3x4","4x4"], index=2, key="cb_grid")
    with col2:
        st.markdown("**PODD Core:** yes, no, more, help, I want, I feel")
    
    cb_cells = []
    cols_n, rows_n = map(int, cb_grid.split("x"))
    total = cols_n * rows_n
    
    board_cards = [{"symbol":c.get("symbol_key"),"tx":c.get("ti"),"id":c.get("id")} for c in ALL_CARDS]
    
    cols = st.columns(cols_n)
    for i in range(total):
        with cols[i % cols_n]:
            sel = st.selectbox(f"Cell", options=[None]+board_cards,
                             format_func=lambda x: x['tx'] if x else "-- Empty --",
                             key=f"cb_cell_{i}", label_visibility="collapsed")
            if sel:
                preview_url = get_arasaac_symbol_url(sel['symbol'])
                if preview_url:
                    st.image(preview_url, width=50)
            cb_cells.append(sel if sel else {"symbol":"","tx":""})
    
    if st.button("➕ Add to Queue", type="primary", use_container_width=True):
        add_to_queue_with_defaults({
            "type":"board",
            "data":{"title":cb_title,"gridSize":cb_grid,"cells":cb_cells}
        })
        st.success("✅ Added")
        st.rerun()

# TAB 6: Regulation Tools ----------------------------------------------------
with tabs[5]:
    st.markdown('<div class="section-card"><h3>Regulation Tools</h3></div>', unsafe_allow_html=True)
    
    tool_type = st.radio("Tool type", ["Zones of Regulation","5-Point Scale","Feelings Chart","Calm-Down"], horizontal=True)
    
    if tool_type == "Zones of Regulation":
        for zone, zd in ZONE_DATA.items():
            st.markdown(f"""<div class="zone zone-{zone}">
                <h4>{zd['name']}</h4>
                <div class="feels">{' • '.join(zd['feels'])}</div>
            </div>""", unsafe_allow_html=True)
        
        if st.button("➕ Add to Queue", use_container_width=True):
            add_to_queue_with_defaults({"type":"regulation","data":{"tool":"zones"}})
            st.success("✅")
            st.rerun()
    
    elif tool_type == "5-Point Scale":
        fp_student = st.text_input("Student name", key="fp_student")
        fp_labels = []
        cols = st.columns(5)
        for i in range(5):
            with cols[i]:
                st.markdown(f'<div style="text-align:center;font-size:1.5rem;background:{FIVE_COLORS[i]};padding:.5rem;border-radius:8px">{i+1}</div>', unsafe_allow_html=True)
                lbl = st.text_input(f"Level", value=["calm","okay","worried","upset","very upset"][i], key=f"fp_{i}", label_visibility="collapsed")
                fp_labels.append(lbl)
        
        if st.button("➕ Add to Queue", use_container_width=True):
            add_to_queue_with_defaults({"type":"regulation","data":{"tool":"fivepoint","student":fp_student,"labels":fp_labels}})
            st.success("✅")
            st.rerun()
    
    elif tool_type == "Feelings Chart":
        fc_cols = st.columns(4)
        fc_selected = []
        for i, (symbol_key, label) in enumerate(FEELINGS_PODD):
            with fc_cols[i % 4]:
                symbol_url = get_arasaac_symbol_url(symbol_key)
                if symbol_url:
                    st.image(symbol_url, width=60)
                if st.checkbox(label, key=f"fc_{i}", value=(i<4)):
                    fc_selected.append((symbol_key, label))
        
        if st.button("➕ Add to Queue", use_container_width=True):
            if fc_selected:
                add_to_queue_with_defaults({"type":"regulation","data":{"tool":"feelings","feels":fc_selected}})
                st.success("✅")
                st.rerun()
    
    elif tool_type == "Calm-Down":
        cd_title = st.text_input("Title", value="I can calm down", key="cd_title")
        cd_cols = st.columns(3)
        cd_selected = []
        for i, strat in enumerate(CALM_STRATEGIES_PODD):
            with cd_cols[i % 3]:
                symbol_url = get_arasaac_symbol_url(strat['symbol_key'])
                if symbol_url:
                    st.image(symbol_url, width=50)
                if st.checkbox(strat['lb'], key=f"cd_{i}", value=(i<6)):
                    cd_selected.append(strat)
        
        if st.button("➕ Add to Queue", use_container_width=True):
            if cd_selected:
                add_to_queue_with_defaults({"type":"regulation","data":{"tool":"calmdown","title":cd_title,"strats":cd_selected}})
                st.success("✅")
                st.rerun()

# TAB 7: Social Scripts ------------------------------------------------------
with tabs[6]:
    st.markdown('<div class="section-card"><h3>Social Script</h3></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2,3])
    with col1:
        ss_student = st.text_input("Student name", key="ss_student")
        ss_title = st.text_input("Script title", value="How to ask for help", key="ss_title")
        ss_steps_n = st.number_input("Steps", min_value=2, max_value=8, value=4, key="ss_steps_n")
    with col2:
        st.markdown("**PODD:** Use 'I will...', 'I can...'")
    
    ss_steps = []
    for i in range(ss_steps_n):
        col_s, col_t, col_p = st.columns([1,3,1])
        with col_s:
            symbol_options = ["number"] + [c.get("symbol_key") for c in ALL_CARDS]
            sym = st.selectbox(f"Symbol", options=symbol_options, key=f"ss_sym_{i}", 
                             label_visibility="collapsed", format_func=lambda x: f"{i+1}" if x == "number" else "Symbol")
        with col_t:
            tx = st.text_input(f"Step", key=f"ss_tx_{i}", label_visibility="collapsed")
        with col_p:
            if sym != "number":
                preview_url = get_arasaac_symbol_url(sym)
                if preview_url:
                    st.image(preview_url, width=30)
        if tx:
            ss_steps.append({"symbol":sym if sym != "number" else f"{i+1}","tx":tx,"is_num":(sym=="number")})
    
    if st.button("➕ Add to Queue", type="primary", use_container_width=True):
        if ss_steps:
            add_to_queue_with_defaults({"type":"script","data":{"student":ss_student,"title":ss_title,"steps":ss_steps}})
            st.success("✅")
            st.rerun()

# TAB 8: Skillstreaming -----------------------------------------------------
with tabs[7]:
    st.markdown('<div class="section-card"><h3>Skillstreaming</h3></div>', unsafe_allow_html=True)
    
    skill_cat = st.selectbox("Category", options=list(SKILLSTREAMING_SKILLS.keys()),
                            format_func=lambda x: f"{SKILLSTREAMING_SKILLS[x]['icon']} {SKILLSTREAMING_SKILLS[x]['name']}")
    
    cat_data = SKILLSTREAMING_SKILLS[skill_cat]
    
    for skill in cat_data['skills']:
        with st.expander(f"✨ {skill['name']}"):
            for i, step in enumerate(skill['steps']):
                st.markdown(f"{i+1}. {step}")
            
            col1, col2 = st.columns([3,1])
            with col1:
                student_name = st.text_input("Student", key=f"skill_{skill_cat}_{skill['name']}", 
                                            label_visibility="collapsed", placeholder="Student name (optional)")
            with col2:
                if st.button("➕", key=f"add_skill_{skill_cat}_{skill['name']}", use_container_width=True):
                    add_to_queue_with_defaults({
                        "type":"skillstreaming",
                        "data":{
                            "student":student_name,
                            "category":cat_data['name'],
                            "skill_name":skill['name'],
                            "steps":skill['steps'],
                            "color":cat_data['color']
                        }
                    })
                    st.success("✅")
                    st.rerun()

# TAB 9: Print Queue with Individual Settings ----------------------------
with tabs[8]:
    st.markdown('<div class="section-card"><h3>Print Queue</h3></div>', unsafe_allow_html=True)
    
    if not st.session_state.vst_print_queue:
        st.info("📭 Empty. Add items from other tabs.")
    else:
        col_queue, col_settings = st.columns([1, 2])
        
        with col_queue:
            st.markdown(f"### {len(st.session_state.vst_print_queue)} Items")
            
            for i, item in enumerate(st.session_state.vst_print_queue):
                is_selected = (st.session_state.vst_selected_item_index == i)
                
                t = item["type"]
                d = item["data"]
                
                if t == "cards":
                    label = f"📇 {d[0].get('ti','')}"
                elif t == "board":
                    label = f"💬 {d.get('title','')}"
                elif t == "firstthen":
                    label = f"➡️ {d.get('title','')}"
                elif t == "schedule":
                    label = f"📅 {d.get('title','')}"
                elif t == "regulation":
                    label = f"🧘 Regulation"
                elif t == "script":
                    label = f"📜 {d.get('title','')}"
                elif t == "skillstreaming":
                    label = f"🎯 {d.get('skill_name','')}"
                
                item_class = "selected" if is_selected else ""
                st.markdown(f'<div class="queue-item {item_class}">{label}</div>', unsafe_allow_html=True)
                
                col_sel, col_del = st.columns([3, 1])
                with col_sel:
                    if st.button("Select", key=f"sel_{i}", use_container_width=True):
                        st.session_state.vst_selected_item_index = i
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_{i}"):
                        st.session_state.vst_print_queue.pop(i)
                        if st.session_state.vst_selected_item_index == i:
                            st.session_state.vst_selected_item_index = None
                        st.rerun()
            
            if st.button("🗑️ Clear All", use_container_width=True):
                st.session_state.vst_print_queue = []
                st.session_state.vst_selected_item_index = None
                st.rerun()
        
        with col_settings:
            if st.session_state.vst_selected_item_index is not None:
                st.markdown(f"### Settings: Item #{st.session_state.vst_selected_item_index + 1}")
                
                settings = st.session_state.vst_print_queue[st.session_state.vst_selected_item_index]['print_settings']
                
                col_l, col_r = st.columns(2)
                
                with col_l:
                    st.markdown("**Page**")
                    orientation = st.radio("Orientation", ["Portrait", "Landscape"], 
                                         index=0 if settings['orientation']=='Portrait' else 1, key="orient")
                    page_size = st.selectbox("Size", ["A4", "Letter (US)", "A5", "Lanyard (85mm x 54mm)"],
                                           index=["A4", "Letter (US)", "A5", "Lanyard (85mm x 54mm)"].index(settings['page_size']),
                                           key="size")
                    cards_pp = st.select_slider("Cards/Page", [1, 2, 4, 6, 8], value=settings['cards_per_page'], key="cpp")
                
                with col_r:
                    st.markdown("**Card**")
                    symbol_sz = st.slider("Symbol", 30, 150, settings['symbol_size'], 10, format="%dpx", key="sym")
                    title_sz = st.slider("Title", 8, 24, settings['title_size'], 1, format="%dpt", key="tit")
                    sub_sz = st.slider("Subtitle", 6, 18, settings['subtitle_size'], 1, format="%dpt", key="sub")
                
                # Update
                settings.update({
                    'orientation': orientation,
                    'page_size': page_size,
                    'cards_per_page': cards_pp,
                    'symbol_size': symbol_sz,
                    'title_size': title_sz,
                    'subtitle_size': sub_sz
                })
                
                # Preview
                st.markdown("### Preview")
                st.markdown(f'<span class="size-badge">{orientation}</span><span class="size-badge">{page_size}</span><span class="size-badge">{cards_pp} cards/pg</span><span class="size-badge">Symbol: {symbol_sz}px</span>', unsafe_allow_html=True)
                
                st.divider()
                
                col_one, col_all = st.columns(2)
                with col_one:
                    st.download_button("⬇️ This Item", data="HTML_HERE", file_name=f"item_{st.session_state.vst_selected_item_index + 1}.html",
                                     mime="text/html", type="primary", use_container_width=True)
                with col_all:
                    st.download_button("⬇️ All Items", data="HTML_HERE", file_name="all_items.html",
                                     mime="text/html", use_container_width=True)
            else:
                st.info("👈 Select item to adjust")
