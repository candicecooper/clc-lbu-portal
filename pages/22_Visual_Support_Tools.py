# =============================================================================
# 22_Visual_Support_Tools.py  -  CLC-LBU Portal
# ADVANCED VERSION - Individual item settings + Custom card library + Search
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
# DATA - DEFAULT CARDS + CUSTOM CARDS
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

# Skillstreaming (abbreviated for space)
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
# HELPER FUNCTION - Generate HTML for items
# =============================================================================

def generate_html_for_items(items_list, single_item=False):
    """Generate print-ready HTML for one or more items with their individual settings"""
    
    html_parts = ['<!DOCTYPE html><html><head><meta charset="UTF-8">']
    html_parts.append('<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap" rel="stylesheet">')
    html_parts.append('<style>*{box-sizing:border-box;margin:0;padding:0;font-family:"Nunito",sans-serif}body{background:#fff}</style>')
    html_parts.append('</head><body>')
    
    for item_idx, item in enumerate(items_list):
        settings = item.get('print_settings', {})
        
        # Extract settings
        orientation = settings.get('orientation', 'Portrait')
        page_size = settings.get('page_size', 'A4')
        symbol_size = settings.get('symbol_size', 80)
        title_size = settings.get('title_size', 14)
        subtitle_size = settings.get('subtitle_size', 10)
        card_padding = settings.get('card_padding', 15)
        
        # Page dimensions
        if page_size == "A4":
            page_dims = "210mm 297mm" if orientation == "Portrait" else "297mm 210mm"
        elif page_size == "Letter (US)":
            page_dims = "8.5in 11in" if orientation == "Portrait" else "11in 8.5in"
        elif page_size == "A5":
            page_dims = "148mm 210mm" if orientation == "Portrait" else "210mm 148mm"
        else:
            page_dims = "85mm 54mm"
        
        # Add page with settings for this item
        html_parts.append(f'<div style="page-break-after:always"><style>@page{{size:{page_dims};margin:6mm}}</style>')
        
        t = item["type"]
        d = item["data"]
        
        # Generate content based on type
        if t == "cards":
            for card in d:
                symbol_url = get_arasaac_symbol_url(card.get('symbol_key', ''))
                html_parts.append(f'<div style="border:2px solid {card.get("color","#1A5C78")};border-radius:12px;padding:{card_padding}px;text-align:center;background:#fff;max-width:400px;margin:20px auto">')
                if symbol_url:
                    html_parts.append(f'<img src="{symbol_url}" style="width:{symbol_size}px;height:{symbol_size}px;object-fit:contain;margin:0 auto {card_padding}px;display:block">')
                html_parts.append(f'<div style="font-size:{title_size}pt;font-weight:800;margin-bottom:8px">{card.get("ti","")}</div>')
                html_parts.append(f'<div style="font-size:{subtitle_size}pt;color:#666">{card.get("sub","")}</div>')
                html_parts.append('</div>')
        
        html_parts.append('</div>')
    
    html_parts.append('</body></html>')
    return "".join(html_parts)

# =============================================================================
# HELPER FUNCTION - Get item print settings
# =============================================================================

def get_item_settings(item_index):
    """Get print settings for specific item, or use defaults"""
    if item_index is not None and item_index < len(st.session_state.vst_print_queue):
        item = st.session_state.vst_print_queue[item_index]
        return item.get('print_settings', {
            'orientation': 'Portrait',
            'page_size': 'A4',
            'cards_per_page': 4,
            'margin_size': 'Small (3mm)',
            'symbol_size': 80,
            'title_size': 14,
            'subtitle_size': 10,
            'border_width': 'Medium (2px)',
            'card_padding': 15
        })
    return None

def update_item_settings(item_index, settings):
    """Update print settings for specific item"""
    if item_index is not None and item_index < len(st.session_state.vst_print_queue):
        st.session_state.vst_print_queue[item_index]['print_settings'] = settings

# =============================================================================
# INTERFACE
# =============================================================================

st.markdown("""
<div class="vst-header">
    <div class="icon">🎨</div>
    <div>
        <h1>Visual Support Tools - Advanced</h1>
        <p>Custom cards • Individual item settings • Search & filter</p>
    </div>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs([
    "📇 Card Library",
    "➕ Create Custom Card",
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
    
    # Filter cards based on search and filters
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
                        st.session_state.vst_print_queue.append({
                            "type":"cards",
                            "data":[c],
                            "print_settings": {
                                'orientation': 'Portrait',
                                'page_size': 'A4',
                                'cards_per_page': 4,
                                'margin_size': 'Small (3mm)',
                                'symbol_size': 80,
                                'title_size': 14,
                                'subtitle_size': 10,
                                'border_width': 'Medium (2px)',
                                'card_padding': 15
                            }
                        })
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
    
    st.markdown("""
    Create your own custom cards and add them to the library. These will be available 
    in the Card Library tab with a purple CUSTOM badge.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        custom_title = st.text_input("Card Title (Main Text)", 
                                     placeholder="e.g., I need a drink",
                                     key="custom_title")
        
        custom_subtitle = st.text_input("Card Subtitle (Small Text)", 
                                       placeholder="e.g., I want water",
                                       key="custom_subtitle")
        
        custom_symbol = st.text_input("ARASAAC Symbol Keyword", 
                                     placeholder="e.g., water, drink, thirsty",
                                     help="This will search ARASAAC for a matching symbol",
                                     key="custom_symbol")
        
        custom_category = st.selectbox("Category",
                                      options=["regulation","communication","actions","social","places","activities"],
                                      key="custom_category")
    
    with col2:
        custom_color = st.color_picker("Card Border Color", value=TEAL, key="custom_color")
        
        custom_frameworks = st.multiselect("Frameworks",
                                          options=list(FW_DETAILS.keys()),
                                          default=["AAC"],
                                          key="custom_frameworks")
        
        st.markdown("**Preview Symbol:**")
        if custom_symbol:
            preview_symbol_url = get_arasaac_symbol_url(custom_symbol)
            if preview_symbol_url:
                st.image(preview_symbol_url, width=100)
            else:
                st.warning("No symbol found - try different keyword")
    
    if st.button("➕ Add Custom Card to Library", type="primary", use_container_width=True):
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
            st.success(f"✅ Added '{custom_title}' to library! Go to Card Library tab to use it.")
            st.rerun()
        else:
            st.error("Please enter at least a title and symbol keyword")

# TAB 3: Print Queue with Individual Settings ----------------------------
with tabs[2]:
    st.markdown('<div class="section-card"><h3>Print Queue</h3></div>', unsafe_allow_html=True)
    
    if not st.session_state.vst_print_queue:
        st.info("📭 Print queue is empty. Add items from the Card Library tab.")
    else:
        col_queue, col_settings = st.columns([1, 2])
        
        with col_queue:
            st.markdown("### Items in Queue")
            st.caption(f"{len(st.session_state.vst_print_queue)} items")
            
            for i, item in enumerate(st.session_state.vst_print_queue):
                is_selected = (st.session_state.vst_selected_item_index == i)
                
                # Build item display
                t = item["type"]
                d = item["data"]
                
                if t == "cards":
                    item_label = f"📇 Card: {d[0].get('ti','')}"
                elif t == "board":
                    item_label = f"💬 Board: {d.get('title','')}"
                elif t == "firstthen":
                    item_label = f"➡️ First-Then: {d.get('title','')}"
                elif t == "schedule":
                    item_label = f"📅 Schedule: {d.get('title','')}"
                elif t == "regulation":
                    item_label = f"🧘 Regulation"
                elif t == "script":
                    item_label = f"📜 Script: {d.get('title','')}"
                elif t == "skillstreaming":
                    item_label = f"🎯 Skill: {d.get('skill_name','')}"
                
                # Item card
                item_class = "selected" if is_selected else ""
                st.markdown(f'<div class="queue-item {item_class}">{item_label}</div>', 
                          unsafe_allow_html=True)
                
                col_sel, col_del = st.columns([3, 1])
                with col_sel:
                    if st.button("Select", key=f"select_{i}", use_container_width=True):
                        st.session_state.vst_selected_item_index = i
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_queue_{i}"):
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
                st.markdown(f"### Settings for Item #{st.session_state.vst_selected_item_index + 1}")
                
                # Get current settings for this item
                current_settings = get_item_settings(st.session_state.vst_selected_item_index)
                
                col_left, col_right = st.columns(2)
                
                with col_left:
                    st.markdown("**Page Settings**")
                    orientation = st.radio("Orientation", ["Portrait", "Landscape"], 
                                         index=0 if current_settings['orientation']=='Portrait' else 1,
                                         key="item_orientation")
                    
                    page_size = st.selectbox("Page Size", 
                                           ["A4", "Letter (US)", "A5", "Lanyard (85mm x 54mm)"],
                                           index=["A4", "Letter (US)", "A5", "Lanyard (85mm x 54mm)"].index(current_settings['page_size']),
                                           key="item_page_size")
                    
                    cards_per_page = st.select_slider("Cards Per Page", 
                                                     options=[1, 2, 4, 6, 8],
                                                     value=current_settings['cards_per_page'],
                                                     key="item_cpp")
                
                with col_right:
                    st.markdown("**Card Settings**")
                    symbol_size = st.slider("Symbol Size", 30, 150, current_settings['symbol_size'], 10, 
                                          format="%dpx", key="item_symbol")
                    
                    title_size = st.slider("Title Size", 8, 24, current_settings['title_size'], 1,
                                         format="%dpt", key="item_title")
                    
                    subtitle_size = st.slider("Subtitle Size", 6, 18, current_settings['subtitle_size'], 1,
                                            format="%dpt", key="item_subtitle")
                
                # Update settings for this item
                new_settings = {
                    'orientation': orientation,
                    'page_size': page_size,
                    'cards_per_page': cards_per_page,
                    'margin_size': 'Small (3mm)',
                    'symbol_size': symbol_size,
                    'title_size': title_size,
                    'subtitle_size': subtitle_size,
                    'border_width': 'Medium (2px)',
                    'card_padding': 15
                }
                update_item_settings(st.session_state.vst_selected_item_index, new_settings)
                
                # Preview
                st.markdown("### Preview")
                st.markdown('<div class="print-preview">', unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f'<span class="size-badge">{orientation}</span>', unsafe_allow_html=True)
                    st.markdown(f'<span class="size-badge">{page_size}</span>', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'<span class="size-badge">{cards_per_page} cards/page</span>', unsafe_allow_html=True)
                    st.markdown(f'<span class="size-badge">Symbol: {symbol_size}px</span>', unsafe_allow_html=True)
                with col3:
                    st.markdown(f'<span class="size-badge">Title: {title_size}pt</span>', unsafe_allow_html=True)
                    st.markdown(f'<span class="size-badge">Subtitle: {subtitle_size}pt</span>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Download options
                st.divider()
                
                col_one, col_all = st.columns(2)
                
                with col_one:
                    # Download single item
                    selected_item = st.session_state.vst_print_queue[st.session_state.vst_selected_item_index]
                    settings = selected_item['print_settings']
                    
                    # Generate HTML for this item
                    html = generate_html_for_items([selected_item], single_item=True)
                    
                    filename = f"visual_support_item_{st.session_state.vst_selected_item_index + 1}.html"
                    
                    st.download_button(
                        label="⬇️ Download This Item Only",
                        data=html,
                        file_name=filename,
                        mime="text/html",
                        type="primary",
                        use_container_width=True
                    )
                
                with col_all:
                    # Download all items with their individual settings
                    html_all = generate_html_for_items(st.session_state.vst_print_queue, single_item=False)
                    
                    st.download_button(
                        label="⬇️ Download All Items",
                        data=html_all,
                        file_name="visual_supports_all_items.html",
                        mime="text/html",
                        use_container_width=True
                    )
                
            else:
                st.info("👈 Select an item from the queue to adjust its settings")
