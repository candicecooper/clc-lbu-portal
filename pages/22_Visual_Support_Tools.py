# =============================================================================
# 22_Visual_Support_Tools.py  -  CLC-LBU Portal
# ENHANCED PRINT CUSTOMIZATION VERSION
# Adjustable sizing, orientation, preview, crop controls
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
        st.sidebar.error(f"Symbol fetch error for '{keyword}': {str(e)}")
    
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
.print-preview h4 {{
    color:{TEAL}; font-size:1.1rem; font-weight:800; margin:0 0 1rem;
}}

.size-badge {{
    display:inline-block; padding:.3rem .6rem; border-radius:6px;
    background:{TEAL_B}; color:{TEAL}; font-size:.75rem; font-weight:700;
    margin-right:.5rem;
}}

.aac-note {{
    background:#FEF7EA; border:1px solid #D4860A; border-radius:8px;
    padding:.8rem 1rem; font-size:.82rem; color:#8C5A0A; margin:1rem 0;
    line-height:1.6;
}}
.aac-note strong {{ color:#D4860A; }}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# DATA - Same as before, abbreviated for space
# =============================================================================

CARDS = [
    dict(id="feelings",   cat="regulation",    color=AMBER,     symbol_key="feel",        ti="I feel",               sub="Tell someone",             fw=["BSEM","ZOR","TI","AAC"]),
    dict(id="help",       cat="regulation",    color=AMBER,     symbol_key="help",        ti="I need help",          sub="Someone help me",          fw=["BSEM","TI","AAC"]),
    dict(id="break",      cat="regulation",    color=AMBER,     symbol_key="break",       ti="I need a break",       sub="I want to stop",           fw=["TI","PBS","BSEM"]),
    dict(id="calm",       cat="regulation",    color=AMBER,     symbol_key="calm",        ti="I need to calm down",  sub="I want quiet",             fw=["BSEM","TI","OT"]),
    dict(id="safe",       cat="regulation",    color=AMBER,     symbol_key="safe",        ti="I feel safe",          sub="It's okay",                fw=["TI","PBS"]),
    dict(id="yes",        cat="communication", color=GREEN,     symbol_key="yes",         ti="Yes",                  sub="I want this",              fw=["AAC","PODD"]),
    dict(id="no",         cat="communication", color=GREEN,     symbol_key="no",          ti="No",                   sub="I don't want this",        fw=["AAC","PODD"]),
    dict(id="more",       cat="communication", color=GREEN,     symbol_key="more",        ti="More",                 sub="I want more",              fw=["AAC","PODD"]),
    dict(id="finished",   cat="communication", color=GREEN,     symbol_key="finished",    ti="Finished",             sub="All done",                 fw=["AAC","PODD"]),
    dict(id="want",       cat="communication", color=GREEN,     symbol_key="want",        ti="I want",               sub="Something I want",         fw=["AAC","PODD"]),
    dict(id="like",       cat="communication", color=GREEN,     symbol_key="like",        ti="I like",               sub="Something I like",         fw=["AAC","PODD"]),
    dict(id="dont_like",  cat="communication", color=GREEN,     symbol_key="dislike",     ti="I don't like",         sub="Something I don't like",   fw=["AAC","PODD"]),
    dict(id="go",         cat="actions",       color="#3730A3", symbol_key="go",          ti="I want to go",         sub="I want to move",           fw=["AAC","PODD"]),
    dict(id="stop",       cat="actions",       color="#3730A3", symbol_key="stop",        ti="I want to stop",       sub="Stop now",                 fw=["AAC","PODD"]),
    dict(id="wait",       cat="actions",       color="#3730A3", symbol_key="wait",        ti="I can wait",           sub="Wait please",              fw=["AAC","PODD"]),
    dict(id="look",       cat="actions",       color="#3730A3", symbol_key="look",        ti="I want to look",       sub="I want to see",            fw=["AAC","PODD"]),
    dict(id="listen",     cat="actions",       color="#3730A3", symbol_key="listen",      ti="I want to listen",     sub="I want to hear",           fw=["AAC","PODD"]),
    dict(id="hello",      cat="social",        color="#8C2D5A", symbol_key="hello",       ti="Hello",                sub="Say hi",                   fw=["AAC","PODD"]),
    dict(id="goodbye",    cat="social",        color="#8C2D5A", symbol_key="goodbye",     ti="Goodbye",              sub="Say bye",                  fw=["AAC","PODD"]),
    dict(id="please",     cat="social",        color="#8C2D5A", symbol_key="please",      ti="Please",               sub="Can I have please",        fw=["AAC","PODD"]),
    dict(id="thankyou",   cat="social",        color="#8C2D5A", symbol_key="thank you",   ti="Thank you",            sub="Thanks",                   fw=["AAC","PODD"]),
    dict(id="sorry",      cat="social",        color="#8C2D5A", symbol_key="sorry",       ti="Sorry",                sub="I am sorry",               fw=["AAC","PODD"]),
    dict(id="bathroom",   cat="places",        color="#0E7490", symbol_key="toilet",      ti="Bathroom",             sub="I want the toilet",        fw=["AAC","PODD"]),
    dict(id="outside",    cat="places",        color="#0E7490", symbol_key="outside",     ti="Outside",              sub="I want to go outside",     fw=["AAC","PODD"]),
    dict(id="home",       cat="places",        color="#0E7490", symbol_key="home",        ti="Home",                 sub="I want to go home",        fw=["AAC","PODD"]),
    dict(id="eat",        cat="activities",    color="#059669", symbol_key="eat",         ti="I want to eat",        sub="Food",                     fw=["AAC","PODD"]),
    dict(id="drink",      cat="activities",    color="#059669", symbol_key="drink",       ti="I want to drink",      sub="Something to drink",       fw=["AAC","PODD"]),
    dict(id="play",       cat="activities",    color="#059669", symbol_key="play",        ti="I want to play",       sub="Play time",                fw=["AAC","PODD"]),
    dict(id="work",       cat="activities",    color="#059669", symbol_key="work",        ti="I want to work",       sub="Do work",                  fw=["AAC","PODD"]),
    dict(id="read",       cat="activities",    color="#059669", symbol_key="read",        ti="I want to read",       sub="Read a book",              fw=["AAC","PODD"]),
]

SKILLSTREAMING_SKILLS = {
    "classroom": {
        "name": "Classroom Survival Skills",
        "color": "#1A5C78",
        "icon": "📚",
        "skills": [
            {"name": "Listening", "steps": ["Look at the person talking", "Think about what is being said", "Wait until the person is done talking", "Say what you want to say"]},
            {"name": "Asking for Help", "steps": ["Decide what the problem is", "Think about asking for help", "Choose who to ask", "Tell that person your problem"]},
            {"name": "Following Instructions", "steps": ["Listen carefully to the instruction", "Think about what you have been asked to do", "Ask questions if you need to", "Repeat the steps to yourself", "Do what you have been asked"]},
        ]
    },
    "friendship": {
        "name": "Friendship-Making Skills",
        "color": "#2D7D4F",
        "icon": "🤝",
        "skills": [
            {"name": "Joining In", "steps": ["Watch what is happening", "Decide if you want to join in", "Decide the best way to join in", "Choose the best time to join in", "Join in"]},
            {"name": "Starting a Conversation", "steps": ["Choose someone to talk to", "Decide what you want to say", "Choose a good time and place", "Start talking in a friendly way"]},
        ]
    },
    "feelings": {
        "name": "Dealing with Feelings",
        "color": "#D4860A",
        "icon": "💭",
        "skills": [
            {"name": "Knowing Your Feelings", "steps": ["Think about how your body feels", "Decide what happened to make you feel this way", "Decide what feeling you are having", "Decide how strong your feeling is"]},
            {"name": "Expressing Your Feelings", "steps": ["Stop and think about what you are feeling", "Decide what it was that made you feel this way", "Decide how you can best express your feeling", "Express your feeling in a calm and friendly way"]},
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
# INTERFACE
# =============================================================================

st.markdown("""
<div class="vst-header">
    <div class="icon">🎨</div>
    <div>
        <h1>Visual Support Tools</h1>
        <p>Professional print customization • Adjustable sizing • ARASAAC symbols</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Initialize session state
if "vst_print_queue" not in st.session_state:
    st.session_state.vst_print_queue = []

tabs = st.tabs([
    "📇 Quick Cards",
    "🎯 Skillstreaming",
    "🖨️ Print Queue & Settings"
])

# TAB 1: Quick Cards (Simplified for demo) ----------------------------------
with tabs[0]:
    st.markdown('<div class="section-card"><h3>Select Quick Cards with REAL Symbols</h3></div>', unsafe_allow_html=True)
    
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
                            st.markdown("<div style='font-size:2.5rem;text-align:center'>📌</div>", unsafe_allow_html=True)
                        
                        st.markdown(f"**{c.get('ti','')}**")
                        st.caption(c.get('sub',''))
                        
                        if st.button(f"Add to print", key=f"add_{c['id']}", use_container_width=True):
                            st.session_state.vst_print_queue.append({"type":"cards","data":[c]})
                            st.success("✅ Added")
                            st.rerun()

# TAB 2: Skillstreaming -----------------------------------------------------
with tabs[1]:
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

# TAB 3: PRINT QUEUE WITH FULL CUSTOMIZATION --------------------------------
with tabs[2]:
    st.markdown('<div class="section-card"><h3>🖨️ Print Queue & Customization</h3></div>', unsafe_allow_html=True)
    
    if not st.session_state.vst_print_queue:
        st.info("📭 Print queue is empty. Add items from other tabs.")
    else:
        st.markdown(f"**{len(st.session_state.vst_print_queue)} item(s) in queue**")
        
        # Show queue with delete buttons
        for i, item in enumerate(st.session_state.vst_print_queue):
            col1, col2 = st.columns([5,1])
            with col1:
                t = item["type"]
                d = item["data"]
                if t == "cards":
                    st.markdown(f"📇 **Quick Cards** ({len(d)} cards)")
                elif t == "skillstreaming":
                    st.markdown(f"🎯 **Skillstreaming:** {d.get('skill_name','')}")
            with col2:
                if st.button("🗑️", key=f"del_{i}"):
                    st.session_state.vst_print_queue.pop(i)
                    st.rerun()
        
        st.divider()
        
        # =====================================================================
        # ENHANCED PRINT CUSTOMIZATION SECTION
        # =====================================================================
        
        st.markdown("## 🎨 Print Customization")
        
        col_left, col_right = st.columns([1, 1])
        
        with col_left:
            st.markdown("### 📐 Page Settings")
            
            # Orientation
            orientation = st.radio(
                "Page Orientation",
                options=["Portrait", "Landscape"],
                horizontal=True,
                help="Choose how the page is oriented"
            )
            
            # Page size
            page_size = st.selectbox(
                "Page Size",
                options=["A4", "Letter (US)", "A5", "Lanyard (85mm x 54mm)"],
                help="Select paper size for printing"
            )
            
            # Cards per page
            if "Lanyard" not in page_size:
                cards_per_page = st.select_slider(
                    "Cards Per Page",
                    options=[1, 2, 4, 6, 8, 9, 12],
                    value=4,
                    help="How many cards to fit on each page"
                )
            else:
                cards_per_page = 8
                st.info("Lanyard cards: 8 per page (standard)")
            
            # Margins
            margin_size = st.select_slider(
                "Page Margins",
                options=["None", "Small (3mm)", "Medium (6mm)", "Large (10mm)"],
                value="Small (3mm)",
                help="White space around the edges"
            )
        
        with col_right:
            st.markdown("### 📏 Card Settings")
            
            # Symbol size
            symbol_size = st.slider(
                "Symbol Size",
                min_value=30,
                max_value=150,
                value=80,
                step=10,
                format="%dpx",
                help="Adjust the size of ARASAAC symbols"
            )
            
            # Title font size
            title_size = st.slider(
                "Title Text Size",
                min_value=8,
                max_value=24,
                value=14,
                step=1,
                format="%dpt",
                help="Size of the main card text"
            )
            
            # Subtitle font size
            subtitle_size = st.slider(
                "Subtitle Text Size",
                min_value=6,
                max_value=18,
                value=10,
                step=1,
                format="%dpt",
                help="Size of the secondary card text"
            )
            
            # Card border
            border_width = st.select_slider(
                "Card Border Thickness",
                options=["None", "Thin (1px)", "Medium (2px)", "Thick (3px)", "Extra Thick (4px)"],
                value="Medium (2px)",
                help="Thickness of card borders"
            )
            
            # Card padding
            card_padding = st.slider(
                "Card Padding",
                min_value=5,
                max_value=30,
                value=15,
                step=5,
                format="%dpx",
                help="Space inside each card"
            )
        
        st.divider()
        
        # =====================================================================
        # PREVIEW SECTION
        # =====================================================================
        
        st.markdown("## 👀 Preview")
        
        # Calculate dimensions
        if page_size == "A4":
            page_width = "210mm"
            page_height = "297mm" if orientation == "Portrait" else "210mm"
        elif page_size == "Letter (US)":
            page_width = "8.5in"
            page_height = "11in" if orientation == "Portrait" else "8.5in"
        elif page_size == "A5":
            page_width = "148mm"
            page_height = "210mm" if orientation == "Portrait" else "148mm"
        else:  # Lanyard
            page_width = "85mm"
            page_height = "54mm"
        
        # Margin conversion
        margin_map = {"None": "0", "Small (3mm)": "3mm", "Medium (6mm)": "6mm", "Large (10mm)": "10mm"}
        margin_css = margin_map[margin_size]
        
        # Border conversion
        border_map = {"None": "0", "Thin (1px)": "1px", "Medium (2px)": "2px", "Thick (3px)": "3px", "Extra Thick (4px)": "4px"}
        border_css = border_map[border_width]
        
        # Calculate grid
        cols_per_row = {1: 1, 2: 2, 4: 2, 6: 3, 8: 4, 9: 3, 12: 4}.get(cards_per_page, 2)
        
        # Preview info
        st.markdown('<div class="print-preview">', unsafe_allow_html=True)
        st.markdown(f"<h4>Print Preview Settings</h4>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<span class="size-badge">Page: {page_width} × {page_height}</span>', unsafe_allow_html=True)
            st.markdown(f'<span class="size-badge">Orientation: {orientation}</span>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<span class="size-badge">Cards/Page: {cards_per_page}</span>', unsafe_allow_html=True)
            st.markdown(f'<span class="size-badge">Grid: {cols_per_row} columns</span>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<span class="size-badge">Symbol: {symbol_size}px</span>', unsafe_allow_html=True)
            st.markdown(f'<span class="size-badge">Margins: {margin_css}</span>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Sample preview card
        st.markdown("### Sample Card Preview:")
        preview_col1, preview_col2, preview_col3 = st.columns([1,2,1])
        with preview_col2:
            # Show a preview of first card in queue
            if st.session_state.vst_print_queue:
                first_item = st.session_state.vst_print_queue[0]
                if first_item["type"] == "cards":
                    sample_card = first_item["data"][0]
                    symbol_url = get_arasaac_symbol_url(sample_card.get('symbol_key', ''))
                    
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
        
        # =====================================================================
        # GENERATE & DOWNLOAD
        # =====================================================================
        
        st.markdown("## ⬇️ Download")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Clear All Items", use_container_width=True):
                st.session_state.vst_print_queue = []
                st.rerun()
        
        with col2:
            # Generate HTML with custom settings
            html_parts = ['<!DOCTYPE html><html><head><meta charset="UTF-8">']
            html_parts.append('<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap" rel="stylesheet">')
            html_parts.append('<style>')
            html_parts.append('*{box-sizing:border-box;margin:0;padding:0;font-family:"Nunito",sans-serif}')
            html_parts.append(f'@page{{size:{page_width} {page_height} {orientation.lower()};margin:{margin_css}}}')
            html_parts.append('body{background:#fff;padding:10px}')
            html_parts.append(f'.page{{display:grid;grid-template-columns:repeat({cols_per_row},1fr);gap:8px;page-break-after:always}}')
            html_parts.append(f'.card{{border:{border_css} solid #dde;border-radius:12px;padding:{card_padding}px;text-align:center;break-inside:avoid;background:#fff}}')
            html_parts.append(f'.symbol{{width:{symbol_size}px;height:{symbol_size}px;object-fit:contain;margin:0 auto {card_padding//2}px;display:block}}')
            html_parts.append(f'.title{{font-size:{title_size}pt;font-weight:800;margin-bottom:5px}}')
            html_parts.append(f'.subtitle{{font-size:{subtitle_size}pt;color:#666}}')
            html_parts.append('.skill-step{padding:8px 0 8px 30px;position:relative;font-size:11pt}')
            html_parts.append('.skill-step::before{content:counter(step);counter-increment:step;position:absolute;left:0;background:#7C2D91;color:#fff;width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11pt;font-weight:700}')
            html_parts.append('</style></head><body>')
            
            # Group items into pages
            all_items = []
            for item in st.session_state.vst_print_queue:
                t = item["type"]
                d = item["data"]
                
                if t == "cards":
                    for card in d:
                        symbol_url = get_arasaac_symbol_url(card.get('symbol_key', ''))
                        card_html = f'<div class="card" style="border-color:{card.get("color","#1A5C78")}">'
                        if symbol_url:
                            card_html += f'<img src="{symbol_url}" class="symbol" alt="{card.get("ti","")}">'
                        card_html += f'<div class="title">{card.get("ti","")}</div>'
                        card_html += f'<div class="subtitle">{card.get("sub","")}</div>'
                        card_html += '</div>'
                        all_items.append(card_html)
                
                elif t == "skillstreaming":
                    steps_html = "".join(f'<div class="skill-step">{s}</div>' for s in d.get("steps",[]))
                    student_name = f"{d.get('student','')}'s " if d.get('student') else ""
                    skill_html = f'<div class="card" style="border-left:4px solid {d.get("color","#7C2D91")};counter-reset:step 0">'
                    skill_html += f'<div class="title">{student_name}{d.get("skill_name","")}</div>'
                    skill_html += f'<div class="subtitle" style="margin-bottom:10px">{d.get("category","")}</div>'
                    skill_html += steps_html
                    skill_html += '</div>'
                    all_items.append(skill_html)
            
            # Create pages
            for i in range(0, len(all_items), cards_per_page):
                page_items = all_items[i:i+cards_per_page]
                html_parts.append('<div class="page">')
                html_parts.extend(page_items)
                html_parts.append('</div>')
            
            html_parts.append('</body></html>')
            print_html = "".join(html_parts)
            
            # Download button
            filename = f"visual_supports_{page_size.replace(' ','_')}_{orientation.lower()}_{cards_per_page}cards.html"
            
            st.download_button(
                label="⬇️ Download Print-Ready HTML",
                data=print_html,
                file_name=filename,
                mime="text/html",
                type="primary",
                use_container_width=True
            )
        
        # Print instructions
        st.markdown("""
        <div class="aac-note">
            <strong>📄 How to Print:</strong>
            1. Open the downloaded HTML file in <strong>Chrome or Edge</strong><br>
            2. Press <strong>Ctrl+P</strong> (Windows) or <strong>Cmd+P</strong> (Mac)<br>
            3. In print settings:<br>
            &nbsp;&nbsp;&nbsp;• Layout: Already set to {orientation}<br>
            &nbsp;&nbsp;&nbsp;• Paper size: Already set to {page_size}<br>
            &nbsp;&nbsp;&nbsp;• Margins: Set to <strong>None</strong> (override our margins)<br>
            &nbsp;&nbsp;&nbsp;• Enable <strong>Background graphics</strong><br>
            4. Print or Save as PDF<br>
            5. Laminate for durability
        </div>
        """.format(orientation=orientation, page_size=page_size), unsafe_allow_html=True)
