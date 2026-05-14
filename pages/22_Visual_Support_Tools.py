# =============================================================================
# 22_Visual_Support_Tools.py  -  CLC-LBU Portal
# ULTIMATE VERSION - All resource types + Individual settings + Custom cards + Search
# =============================================================================

import streamlit as st
import json
import requests
from datetime import datetime
import urllib.parse
from supabase import create_client

st.set_page_config(
    page_title="Visual Support Tools - CLC",
    page_icon="🎨",
    layout="wide",
)

# -- Supabase Setup -----------------------------------------------------------
@st.cache_resource
def get_supabase_client():
    """Get Supabase client"""
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["key"]
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase_client()

# -- Custom Cards Database Functions ------------------------------------------
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_custom_cards_from_db():
    """Load all active custom cards from Supabase"""
    try:
        response = supabase.table('custom_visual_cards').select('*').eq('is_active', True).order('created_at', desc=True).execute()
        
        cards = []
        for row in response.data:
            cards.append({
                'id': row['card_id'],
                'cat': row['category'],
                'color': row['color'],
                'symbol_key': row['symbol_key'],
                'ti': row['title'],
                'sub': row['subtitle'] or '',
                'fw': row['frameworks'] or [],
                'custom': True,
                'db_id': row['id'],  # Keep database ID for updates
                'created_by': row.get('created_by', 'Unknown'),
                'created_at': row['created_at'],
                'notes': row.get('notes', '')
            })
        return cards
    except Exception as e:
        error_msg = str(e)
        
        # Check for specific schema cache error
        if 'PGRST205' in error_msg or 'schema cache' in error_msg:
            st.warning("⚠️ Database table not found in schema cache. This usually happens right after creating the table. Please run the fix_schema_cache.sql file in Supabase SQL editor, wait 10 seconds, then refresh this page.")
        else:
            st.error(f"Error loading custom cards: {error_msg}")
        
        return []  # Return empty list so app doesn't crash

def save_custom_card_to_db(card_data):
    """Save new custom card to Supabase"""
    try:
        db_card = {
            'card_id': card_data['id'],
            'category': card_data['cat'],
            'color': card_data['color'],
            'symbol_key': card_data['symbol_key'],
            'title': card_data['ti'],
            'subtitle': card_data['sub'],
            'frameworks': card_data['fw'],
            'created_by': card_data.get('created_by', 'Staff'),
            'is_active': True
        }
        
        response = supabase.table('custom_visual_cards').insert(db_card).execute()
        
        # Clear cache to reload cards
        load_custom_cards_from_db.clear()
        return True, "Card saved successfully!"
    except Exception as e:
        return False, f"Error saving card: {e}"

def update_custom_card_in_db(db_id, card_data):
    """Update existing custom card in Supabase"""
    try:
        db_card = {
            'category': card_data['cat'],
            'color': card_data['color'],
            'symbol_key': card_data['symbol_key'],
            'title': card_data['ti'],
            'subtitle': card_data['sub'],
            'frameworks': card_data['fw']
        }
        
        response = supabase.table('custom_visual_cards').update(db_card).eq('id', db_id).execute()
        
        # Clear cache to reload cards
        load_custom_cards_from_db.clear()
        return True, "Card updated successfully!"
    except Exception as e:
        return False, f"Error updating card: {e}"

def delete_custom_card_from_db(db_id):
    """Delete (deactivate) custom card from Supabase"""
    try:
        # Soft delete - just set is_active to False
        response = supabase.table('custom_visual_cards').update({'is_active': False}).eq('id', db_id).execute()
        
        # Clear cache to reload cards
        load_custom_cards_from_db.clear()
        return True, "Card deleted successfully!"
    except Exception as e:
        return False, f"Error deleting card: {e}"

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

.core-badge {{
    display:inline-block; padding:.2rem .5rem; border-radius:12px;
    background:#F59E0B; color:#fff; font-size:.65rem; font-weight:700;
    margin-left:.3rem;
}}

.tws-badge {{
    display:inline-block; padding:.2rem .5rem; border-radius:12px;
    background:#3B82F6; color:#fff; font-size:.65rem; font-weight:700;
    margin-left:.3rem;
}}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# DATA
# =============================================================================

DEFAULT_CARDS = [
    # =========================================================================
    # CRESCENDO CORE WORDS - ACTIONS
    # =========================================================================
    dict(id="go",           cat="actions",       color="#3730A3", symbol_key="go",          ti="go",                   sub="Let's go",                 fw=["AAC","PODD","CORE"], custom=False),
    dict(id="stop",         cat="actions",       color="#3730A3", symbol_key="stop",        ti="stop",                 sub="Stop now",                 fw=["AAC","PODD","CORE"], custom=False),
    dict(id="do",           cat="actions",       color="#3730A3", symbol_key="do",          ti="do",                   sub="Do it",                    fw=["AAC","PODD","CORE"], custom=False),
    dict(id="get",          cat="actions",       color="#3730A3", symbol_key="get",         ti="get",                  sub="Get something",            fw=["AAC","PODD","CORE"], custom=False),
    dict(id="make",         cat="actions",       color="#3730A3", symbol_key="make",        ti="make",                 sub="Make something",           fw=["AAC","PODD","CORE"], custom=False),
    dict(id="put",          cat="actions",       color="#3730A3", symbol_key="put",         ti="put",                  sub="Put down",                 fw=["AAC","PODD","CORE"], custom=False),
    dict(id="turn",         cat="actions",       color="#3730A3", symbol_key="turn",        ti="turn",                 sub="Turn around",              fw=["AAC","PODD","CORE"], custom=False),
    dict(id="open",         cat="actions",       color="#3730A3", symbol_key="open",        ti="open",                 sub="Open it",                  fw=["AAC","PODD","CORE"], custom=False),
    dict(id="close",        cat="actions",       color="#3730A3", symbol_key="close",       ti="close",                sub="Close it",                 fw=["AAC","PODD","CORE"], custom=False),
    dict(id="come",         cat="actions",       color="#3730A3", symbol_key="come",        ti="come",                 sub="Come here",                fw=["AAC","PODD","CORE"], custom=False),
    dict(id="look",         cat="actions",       color="#3730A3", symbol_key="look",        ti="look",                 sub="Look at this",             fw=["AAC","PODD","CORE"], custom=False),
    dict(id="listen",       cat="actions",       color="#3730A3", symbol_key="listen",      ti="listen",               sub="Listen carefully",         fw=["AAC","PODD","CORE"], custom=False),
    dict(id="wait",         cat="actions",       color="#3730A3", symbol_key="wait",        ti="wait",                 sub="Wait please",              fw=["AAC","PODD","CORE"], custom=False),
    
    # =========================================================================
    # CRESCENDO CORE WORDS - DESCRIPTORS
    # =========================================================================
    dict(id="more",         cat="communication", color=GREEN,     symbol_key="more",        ti="more",                 sub="I want more",              fw=["AAC","PODD","CORE"], custom=False),
    dict(id="big",          cat="communication", color=GREEN,     symbol_key="big",         ti="big",                  sub="It's big",                 fw=["AAC","PODD","CORE"], custom=False),
    dict(id="little",       cat="communication", color=GREEN,     symbol_key="little",      ti="little",               sub="It's little",              fw=["AAC","PODD","CORE"], custom=False),
    dict(id="different",    cat="communication", color=GREEN,     symbol_key="different",   ti="different",            sub="Something different",      fw=["AAC","PODD","CORE"], custom=False),
    dict(id="same",         cat="communication", color=GREEN,     symbol_key="same",        ti="same",                 sub="The same",                 fw=["AAC","PODD","CORE"], custom=False),
    dict(id="good",         cat="communication", color=GREEN,     symbol_key="good",        ti="good",                 sub="That's good",              fw=["AAC","PODD","CORE"], custom=False),
    dict(id="bad",          cat="communication", color=GREEN,     symbol_key="bad",         ti="bad",                  sub="That's bad",               fw=["AAC","PODD","CORE"], custom=False),
    dict(id="hot",          cat="communication", color=GREEN,     symbol_key="hot",         ti="hot",                  sub="It's hot",                 fw=["AAC","PODD","CORE"], custom=False),
    dict(id="cold",         cat="communication", color=GREEN,     symbol_key="cold",        ti="cold",                 sub="It's cold",                fw=["AAC","PODD","CORE"], custom=False),
    dict(id="all",          cat="communication", color=GREEN,     symbol_key="all",         ti="all",                  sub="All of it",                fw=["AAC","PODD","CORE"], custom=False),
    dict(id="some",         cat="communication", color=GREEN,     symbol_key="some",        ti="some",                 sub="Some of it",               fw=["AAC","PODD","CORE"], custom=False),
    
    # =========================================================================
    # CRESCENDO CORE WORDS - QUESTIONS
    # =========================================================================
    dict(id="what",         cat="communication", color="#8C2D5A", symbol_key="what",        ti="what",                 sub="What is it?",              fw=["AAC","PODD","CORE"], custom=False),
    dict(id="where",        cat="communication", color="#8C2D5A", symbol_key="where",       ti="where",                sub="Where is it?",             fw=["AAC","PODD","CORE"], custom=False),
    dict(id="when",         cat="communication", color="#8C2D5A", symbol_key="when",        ti="when",                 sub="When?",                    fw=["AAC","PODD","CORE"], custom=False),
    dict(id="who",          cat="communication", color="#8C2D5A", symbol_key="who",         ti="who",                  sub="Who is it?",               fw=["AAC","PODD","CORE"], custom=False),
    dict(id="why",          cat="communication", color="#8C2D5A", symbol_key="why",         ti="why",                  sub="Why?",                     fw=["AAC","PODD","CORE"], custom=False),
    dict(id="how",          cat="communication", color="#8C2D5A", symbol_key="how",         ti="how",                  sub="How?",                     fw=["AAC","PODD","CORE"], custom=False),
    
    # =========================================================================
    # CRESCENDO CORE WORDS - PRONOUNS
    # =========================================================================
    dict(id="i",            cat="communication", color=GREEN,     symbol_key="I",           ti="I",                    sub="Me",                       fw=["AAC","PODD","CORE"], custom=False),
    dict(id="you",          cat="communication", color=GREEN,     symbol_key="you",         ti="you",                  sub="You",                      fw=["AAC","PODD","CORE"], custom=False),
    dict(id="my",           cat="communication", color=GREEN,     symbol_key="my",          ti="my",                   sub="Mine",                     fw=["AAC","PODD","CORE"], custom=False),
    dict(id="your",         cat="communication", color=GREEN,     symbol_key="your",        ti="your",                 sub="Yours",                    fw=["AAC","PODD","CORE"], custom=False),
    dict(id="he",           cat="communication", color=GREEN,     symbol_key="he",          ti="he",                   sub="Him",                      fw=["AAC","PODD","CORE"], custom=False),
    dict(id="she",          cat="communication", color=GREEN,     symbol_key="she",         ti="she",                  sub="Her",                      fw=["AAC","PODD","CORE"], custom=False),
    dict(id="we",           cat="communication", color=GREEN,     symbol_key="we",          ti="we",                   sub="Us",                       fw=["AAC","PODD","CORE"], custom=False),
    dict(id="they",         cat="communication", color=GREEN,     symbol_key="they",        ti="they",                 sub="Them",                     fw=["AAC","PODD","CORE"], custom=False),
    
    # =========================================================================
    # CRESCENDO CORE WORDS - LOCATION/TIME
    # =========================================================================
    dict(id="on",           cat="communication", color=GREEN,     symbol_key="on",          ti="on",                   sub="On top",                   fw=["AAC","PODD","CORE"], custom=False),
    dict(id="off",          cat="communication", color=GREEN,     symbol_key="off",         ti="off",                  sub="Take off",                 fw=["AAC","PODD","CORE"], custom=False),
    dict(id="in",           cat="communication", color=GREEN,     symbol_key="in",          ti="in",                   sub="Inside",                   fw=["AAC","PODD","CORE"], custom=False),
    dict(id="out",          cat="communication", color=GREEN,     symbol_key="out",         ti="out",                  sub="Outside",                  fw=["AAC","PODD","CORE"], custom=False),
    dict(id="up",           cat="communication", color=GREEN,     symbol_key="up",          ti="up",                   sub="Go up",                    fw=["AAC","PODD","CORE"], custom=False),
    dict(id="down",         cat="communication", color=GREEN,     symbol_key="down",        ti="down",                 sub="Go down",                  fw=["AAC","PODD","CORE"], custom=False),
    dict(id="here",         cat="communication", color=GREEN,     symbol_key="here",        ti="here",                 sub="Right here",               fw=["AAC","PODD","CORE"], custom=False),
    dict(id="there",        cat="communication", color=GREEN,     symbol_key="there",       ti="there",                sub="Over there",               fw=["AAC","PODD","CORE"], custom=False),
    dict(id="now",          cat="communication", color=GREEN,     symbol_key="now",         ti="now",                  sub="Right now",                fw=["AAC","PODD","CORE"], custom=False),
    dict(id="later",        cat="communication", color=GREEN,     symbol_key="later",       ti="later",                sub="Not now",                  fw=["AAC","PODD","CORE"], custom=False),
    dict(id="again",        cat="communication", color=GREEN,     symbol_key="again",       ti="again",                sub="Do it again",              fw=["AAC","PODD","CORE"], custom=False),
    
    # =========================================================================
    # CRESCENDO CORE WORDS - NEGATION
    # =========================================================================
    dict(id="not",          cat="communication", color="#B91C1C", symbol_key="not",         ti="not",                  sub="Not that",                 fw=["AAC","PODD","CORE"], custom=False),
    dict(id="dont",         cat="communication", color="#B91C1C", symbol_key="don't",       ti="don't",                sub="Don't do it",              fw=["AAC","PODD","CORE"], custom=False),
    dict(id="cant",         cat="communication", color="#B91C1C", symbol_key="can't",       ti="can't",                sub="I can't",                  fw=["AAC","PODD","CORE"], custom=False),
    
    # =========================================================================
    # CORE SOCIAL WORDS
    # =========================================================================
    dict(id="yes",          cat="communication", color=GREEN,     symbol_key="yes",         ti="yes",                  sub="I want this",              fw=["AAC","PODD","CORE"], custom=False),
    dict(id="no",           cat="communication", color=GREEN,     symbol_key="no",          ti="no",                   sub="I don't want this",        fw=["AAC","PODD","CORE"], custom=False),
    dict(id="please",       cat="social",        color="#8C2D5A", symbol_key="please",      ti="please",               sub="Can I have please",        fw=["AAC","PODD","CORE"], custom=False),
    dict(id="thankyou",     cat="social",        color="#8C2D5A", symbol_key="thank you",   ti="thank you",            sub="Thanks",                   fw=["AAC","PODD","CORE"], custom=False),
    dict(id="sorry",        cat="social",        color="#8C2D5A", symbol_key="sorry",       ti="sorry",                sub="I am sorry",               fw=["AAC","PODD","CORE"], custom=False),
    dict(id="hello",        cat="social",        color="#8C2D5A", symbol_key="hello",       ti="hello",                sub="Say hi",                   fw=["AAC","PODD","CORE"], custom=False),
    dict(id="goodbye",      cat="social",        color="#8C2D5A", symbol_key="goodbye",     ti="goodbye",              sub="Say bye",                  fw=["AAC","PODD","CORE"], custom=False),
    
    # =========================================================================
    # CORE WANTING/NEEDING (High frequency regulation)
    # =========================================================================
    dict(id="want",         cat="communication", color=GREEN,     symbol_key="want",        ti="want",                 sub="I want",                   fw=["AAC","PODD","CORE"], custom=False),
    dict(id="like",         cat="communication", color=GREEN,     symbol_key="like",        ti="like",                 sub="I like",                   fw=["AAC","PODD","CORE"], custom=False),
    dict(id="dont_like",    cat="communication", color=GREEN,     symbol_key="dislike",     ti="don't like",           sub="I don't like",             fw=["AAC","PODD","CORE"], custom=False),
    dict(id="need",         cat="regulation",    color=AMBER,     symbol_key="need",        ti="need",                 sub="I need",                   fw=["AAC","PODD","CORE"], custom=False),
    dict(id="help",         cat="regulation",    color=AMBER,     symbol_key="help",        ti="help",                 sub="Someone help me",          fw=["BSEM","TI","AAC","CORE"], custom=False),
    dict(id="finished",     cat="communication", color=GREEN,     symbol_key="finished",    ti="finished",             sub="All done",                 fw=["AAC","PODD","CORE"], custom=False),
    
    # =========================================================================
    # REGULATION WORDS (BSEM-aligned)
    # =========================================================================
    dict(id="feel",         cat="regulation",    color=AMBER,     symbol_key="feel",        ti="feel",                 sub="I feel",                   fw=["BSEM","ZOR","TI","AAC","CORE"], custom=False),
    dict(id="break",        cat="regulation",    color=AMBER,     symbol_key="break",       ti="break",                sub="I need a break",           fw=["TI","PBS","BSEM"], custom=False),
    dict(id="calm",         cat="regulation",    color=AMBER,     symbol_key="calm",        ti="calm",                 sub="I want to calm down",      fw=["BSEM","TI","OT"], custom=False),
    dict(id="safe",         cat="regulation",    color=AMBER,     symbol_key="safe",        ti="safe",                 sub="I feel safe",              fw=["TI","PBS"], custom=False),
    
    # =========================================================================
    # FRINGE VOCABULARY - PLACES
    # =========================================================================
    dict(id="bathroom",     cat="places",        color="#0E7490", symbol_key="toilet",      ti="bathroom",             sub="I want the toilet",        fw=["AAC","PODD"], custom=False),
    dict(id="outside",      cat="places",        color="#0E7490", symbol_key="outside",     ti="outside",              sub="I want to go outside",     fw=["AAC","PODD"], custom=False),
    dict(id="home",         cat="places",        color="#0E7490", symbol_key="home",        ti="home",                 sub="I want to go home",        fw=["AAC","PODD"], custom=False),
    
    # =========================================================================
    # FRINGE VOCABULARY - ACTIVITIES
    # =========================================================================
    dict(id="eat",          cat="activities",    color="#059669", symbol_key="eat",         ti="eat",                  sub="I want to eat",            fw=["AAC","PODD"], custom=False),
    dict(id="drink",        cat="activities",    color="#059669", symbol_key="drink",       ti="drink",                sub="I want to drink",          fw=["AAC","PODD"], custom=False),
    dict(id="play",         cat="activities",    color="#059669", symbol_key="play",        ti="play",                 sub="I want to play",           fw=["AAC","PODD"], custom=False),
    dict(id="work",         cat="activities",    color="#059669", symbol_key="work",        ti="work",                 sub="I want to work",           fw=["AAC","PODD"], custom=False),
    dict(id="read",         cat="activities",    color="#059669", symbol_key="read",        ti="read",                 sub="I want to read",           fw=["AAC","PODD"], custom=False),
    
    # =========================================================================
    # TWO WAY STREET - PARTNER STRATEGY CARDS
    # =========================================================================
    dict(id="wait_partner", cat="social",        color="#7C2D91", symbol_key="wait",        ti="WAIT",                 sub="Count to 10 (partner)",    fw=["AAC","TWS"], custom=False),
    dict(id="model_partner",cat="social",        color="#7C2D91", symbol_key="point",       ti="MODEL",                sub="Point, don't test",        fw=["AAC","TWS"], custom=False),
    dict(id="presume",      cat="social",        color="#7C2D91", symbol_key="think",       ti="PRESUME",              sub="They understand",          fw=["AAC","TWS"], custom=False),
    dict(id="honor",        cat="social",        color="#7C2D91", symbol_key="accept",      ti="HONOR",                sub="All communication counts", fw=["AAC","TWS"], custom=False),
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
    "CORE":  {"label":"CORE",  "bg":"#F59E0B","color":"#fff"},  # Gold for core words
    "TWS":   {"label":"TWS",   "bg":"#3B82F6","color":"#fff"},  # Blue for Two Way Street
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
    # Load custom cards from database on first load
    st.session_state.vst_custom_cards = load_custom_cards_from_db()

if "vst_selected_item_index" not in st.session_state:
    st.session_state.vst_selected_item_index = None

if "vst_search_query" not in st.session_state:
    st.session_state.vst_search_query = ""

if "vst_editing_card" not in st.session_state:
    st.session_state.vst_editing_card = None

# Reload custom cards from DB (with cache, so not every render)
st.session_state.vst_custom_cards = load_custom_cards_from_db()

# Combine default and custom cards
ALL_CARDS = DEFAULT_CARDS + st.session_state.vst_custom_cards

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_print_html(items_list):
    """Generate complete print-ready HTML for one or multiple items with their settings"""
    
    html_parts = ['''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Nunito', sans-serif; }
body { background: #fff; }
.page-break { page-break-after: always; }
.card-container { 
    border: 2px solid #333; 
    border-radius: 12px; 
    padding: 15px; 
    text-align: center; 
    background: #fff; 
    break-inside: avoid;
    margin: 10px;
}
.symbol { display: block; margin: 0 auto; }
.title { font-weight: 800; margin: 8px 0; }
.subtitle { color: #666; }
@media print {
    body { background: #fff; }
    .page-break { page-break-after: always; }
}
</style>
</head>
<body>
''']
    
    for item_idx, item in enumerate(items_list):
        settings = item.get('print_settings', {})
        t = item["type"]
        d = item["data"]
        
        # Extract settings
        orientation = settings.get('orientation', 'Portrait')
        page_size = settings.get('page_size', 'A4')
        symbol_size = settings.get('symbol_size', 80)
        title_size = settings.get('title_size', 14)
        subtitle_size = settings.get('subtitle_size', 10)
        padding = settings.get('card_padding', 15)
        
        # Add page styling for this item
        if page_size == "A4":
            page_dims = "210mm 297mm" if orientation == "Portrait" else "297mm 210mm"
        elif page_size == "Letter (US)":
            page_dims = "8.5in 11in" if orientation == "Portrait" else "11in 8.5in"
        elif page_size == "A5":
            page_dims = "148mm 210mm" if orientation == "Portrait" else "210mm 148mm"
        else:
            page_dims = "85mm 54mm"
        
        html_parts.append(f'<style>@page {{ size: {page_dims}; margin: 10mm; }}</style>')
        
        # Generate content based on type
        if t == "cards":
            for card in d:
                symbol_url = get_arasaac_symbol_url(card.get('symbol_key', ''))
                html_parts.append(f'<div class="card-container" style="border-color:{card.get("color","#1A5C78")};padding:{padding}px;max-width:500px;margin:20px auto">')
                if symbol_url:
                    html_parts.append(f'<img src="{symbol_url}" class="symbol" style="width:{symbol_size}px;height:{symbol_size}px;object-fit:contain;margin-bottom:{padding}px">')
                html_parts.append(f'<div class="title" style="font-size:{title_size}pt">{card.get("ti","")}</div>')
                html_parts.append(f'<div class="subtitle" style="font-size:{subtitle_size}pt">{card.get("sub","")}</div>')
                html_parts.append('</div>')
        
        elif t == "board":
            cols_n = int(d.get('gridSize','3x3').split('x')[0])
            html_parts.append(f'<div class="card-container" style="padding:{padding}px;max-width:700px;margin:20px auto">')
            html_parts.append(f'<div class="title" style="font-size:{title_size}pt;margin-bottom:{padding}px">{d.get("title","")}</div>')
            html_parts.append(f'<div style="display:grid;grid-template-columns:repeat({cols_n},1fr);gap:10px">')
            for cell in d.get('cells',[]):
                symbol_url = get_arasaac_symbol_url(cell.get('symbol','')) if cell.get('symbol') else None
                html_parts.append('<div style="border:2px solid #ddd;border-radius:8px;padding:10px;text-align:center">')
                if symbol_url:
                    html_parts.append(f'<img src="{symbol_url}" style="width:{symbol_size//2}px;height:{symbol_size//2}px;object-fit:contain;margin:0 auto 8px">')
                html_parts.append(f'<div style="font-size:{subtitle_size}pt;font-weight:700">{cell.get("tx","")}</div>')
                html_parts.append('</div>')
            html_parts.append('</div></div>')
        
        elif t == "firstthen":
            student = f"{d.get('student','')}'s " if d.get('student') else ""
            html_parts.append(f'<div class="card-container" style="padding:{padding}px;max-width:700px;margin:20px auto">')
            html_parts.append(f'<div class="title" style="font-size:{title_size}pt;margin-bottom:{padding}px">{student}{d.get("title","")}</div>')
            html_parts.append('<div style="display:flex;gap:15px;justify-content:center">')
            for lbl, slot in zip(d.get('labels',[]), d.get('slots',[])):
                if slot:
                    symbol_url = get_arasaac_symbol_url(slot.get('symbol',''))
                    html_parts.append(f'<div style="flex:1;max-width:200px;border:3px solid #1A5C78;border-radius:10px;padding:{padding}px;text-align:center">')
                    html_parts.append(f'<div style="font-size:{subtitle_size+2}pt;font-weight:800;color:#666;margin-bottom:10px">{lbl}</div>')
                    if symbol_url:
                        html_parts.append(f'<img src="{symbol_url}" style="width:{symbol_size}px;height:{symbol_size}px;object-fit:contain;margin:0 auto 10px">')
                    html_parts.append(f'<div style="font-size:{subtitle_size}pt;font-weight:700">{slot.get("lb","")}</div>')
                    html_parts.append('</div>')
            html_parts.append('</div></div>')
        
        elif t == "schedule":
            student = f"{d.get('student','')}'s " if d.get('student') else ""
            html_parts.append(f'<div class="card-container" style="padding:{padding}px;max-width:600px;margin:20px auto">')
            html_parts.append(f'<div class="title" style="font-size:{title_size}pt;margin-bottom:{padding}px">{student}{d.get("title","")}</div>')
            for slot in d.get('slots',[]):
                symbol_url = get_arasaac_symbol_url(slot.get('symbol',''))
                html_parts.append('<div style="display:flex;align-items:center;gap:15px;padding:10px 0;border-bottom:1px solid #eee">')
                html_parts.append(f'<span style="font-size:{subtitle_size+2}pt;font-weight:800;color:#666;min-width:60px">{slot.get("time","")}</span>')
                if symbol_url:
                    html_parts.append(f'<img src="{symbol_url}" style="width:{symbol_size//2}px;height:{symbol_size//2}px;object-fit:contain">')
                html_parts.append(f'<span style="font-size:{subtitle_size}pt;font-weight:700">{slot.get("act","")}</span>')
                html_parts.append('</div>')
            html_parts.append('</div>')
        
        elif t == "regulation":
            tool = d.get('tool','')
            html_parts.append(f'<div class="card-container" style="padding:{padding}px;max-width:700px;margin:20px auto">')
            
            if tool == "zones":
                html_parts.append(f'<div class="title" style="font-size:{title_size}pt;margin-bottom:{padding}px">Zones of Regulation</div>')
                for zone, zdata in ZONE_DATA.items():
                    html_parts.append(f'<div style="background:{zdata["bg"]};border:2px solid {zdata["color"]};border-radius:10px;padding:15px;margin:10px 0">')
                    html_parts.append(f'<div style="font-size:{subtitle_size+2}pt;font-weight:800;margin-bottom:5px">{zdata["name"]}</div>')
                    html_parts.append(f'<div style="font-size:{subtitle_size}pt">{" • ".join(zdata["feels"])}</div>')
                    html_parts.append('</div>')
            
            elif tool == "fivepoint":
                student = f"{d.get('student','')}'s " if d.get('student') else ""
                html_parts.append(f'<div class="title" style="font-size:{title_size}pt;margin-bottom:{padding}px">{student}5-Point Scale</div>')
                html_parts.append('<div style="display:flex;gap:10px">')
                for i, label in enumerate(d.get('labels',[])):
                    html_parts.append(f'<div style="flex:1;text-align:center;border:2px solid {FIVE_COLORS[i]};border-radius:8px;padding:15px;background:{FIVE_COLORS[i]}">')
                    html_parts.append(f'<div style="font-size:{title_size+4}pt;font-weight:800;margin-bottom:10px">{i+1}</div>')
                    html_parts.append(f'<div style="font-size:{subtitle_size}pt;font-weight:700">{label}</div>')
                    html_parts.append('</div>')
                html_parts.append('</div>')
            
            elif tool == "feelings":
                html_parts.append(f'<div class="title" style="font-size:{title_size}pt;margin-bottom:{padding}px">I feel</div>')
                html_parts.append('<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px">')
                for symbol_key, label in d.get('feels',[]):
                    symbol_url = get_arasaac_symbol_url(symbol_key)
                    html_parts.append('<div style="border:2px solid #ddd;border-radius:8px;padding:10px;text-align:center">')
                    if symbol_url:
                        html_parts.append(f'<img src="{symbol_url}" style="width:{symbol_size//2}px;height:{symbol_size//2}px;object-fit:contain;margin:0 auto 8px">')
                    html_parts.append(f'<div style="font-size:{subtitle_size}pt;font-weight:700">{label}</div>')
                    html_parts.append('</div>')
                html_parts.append('</div>')
            
            elif tool == "calmdown":
                html_parts.append(f'<div class="title" style="font-size:{title_size}pt;margin-bottom:{padding}px">{d.get("title","")}</div>')
                html_parts.append('<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">')
                for strat in d.get('strats',[]):
                    symbol_url = get_arasaac_symbol_url(strat.get('symbol_key',''))
                    html_parts.append('<div style="text-align:center;padding:10px">')
                    if symbol_url:
                        html_parts.append(f'<img src="{symbol_url}" style="width:{symbol_size//2}px;height:{symbol_size//2}px;object-fit:contain;margin:0 auto 8px">')
                    html_parts.append(f'<div style="font-size:{subtitle_size}pt;font-weight:700">{strat.get("lb","")}</div>')
                    html_parts.append('</div>')
                html_parts.append('</div>')
            
            html_parts.append('</div>')
        
        elif t == "script":
            student = f"{d.get('student','')}'s " if d.get('student') else ""
            html_parts.append(f'<div class="card-container" style="padding:{padding}px;max-width:600px;margin:20px auto">')
            html_parts.append(f'<div class="title" style="font-size:{title_size}pt;margin-bottom:{padding}px">{student}{d.get("title","")}</div>')
            for step in d.get('steps',[]):
                html_parts.append('<div style="display:flex;align-items:flex-start;gap:12px;margin:12px 0">')
                if step.get('is_num'):
                    html_parts.append(f'<div style="min-width:30px;height:30px;border-radius:50%;background:#1A5C78;color:#fff;display:flex;align-items:center;justify-content:center;font-size:{subtitle_size+2}pt;font-weight:800;flex-shrink:0">{step["symbol"]}</div>')
                else:
                    symbol_url = get_arasaac_symbol_url(step.get('symbol',''))
                    if symbol_url:
                        html_parts.append(f'<img src="{symbol_url}" style="width:40px;height:40px;object-fit:contain;flex-shrink:0">')
                html_parts.append(f'<div style="font-size:{subtitle_size}pt;line-height:1.6;flex:1">{step.get("tx","")}</div>')
                html_parts.append('</div>')
            html_parts.append('</div>')
        
        elif t == "skillstreaming":
            student = f"{d.get('student','')}'s " if d.get('student') else ""
            html_parts.append(f'<div class="card-container" style="border-left:5px solid {d.get("color","#7C2D91")};padding:{padding}px;max-width:600px;margin:20px auto">')
            html_parts.append(f'<div class="title" style="font-size:{title_size}pt">{student}{d.get("skill_name","")}</div>')
            html_parts.append(f'<div style="font-size:{subtitle_size}pt;color:#666;margin-bottom:{padding}px">{d.get("category","")}</div>')
            for i, step in enumerate(d.get("steps",[])):
                html_parts.append(f'<div style="padding:10px 0 10px 40px;position:relative;font-size:{subtitle_size}pt">')
                html_parts.append(f'<span style="position:absolute;left:0;top:10px;width:28px;height:28px;border-radius:50%;background:{d.get("color","#7C2D91")};color:#fff;display:flex;align-items:center;justify-content:center;font-weight:800">{i+1}</span>')
                html_parts.append(f'{step}</div>')
            html_parts.append('</div>')
        
        # Add page break between items (except last one)
        if item_idx < len(items_list) - 1:
            html_parts.append('<div class="page-break"></div>')
    
    html_parts.append('</body></html>')
    return "".join(html_parts)

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
        <h1>Visual Support Tools - AAC Enhanced</h1>
        <p>Proloquo2Go aligned • Two Way Street • 83 core + fringe words • Individual settings</p>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="aac-note">
    <strong>✨ NEW: AAC-Aligned Vocabulary!</strong> This tool now includes 53 <strong>Crescendo core words</strong> 
    (the high-frequency words that make up 80% of communication) aligned with Proloquo2Go. 
    <strong>Gold "CORE" badges</strong> show core words. <strong>Blue "TWS" badges</strong> show Two Way Street 
    partner strategy cards. Use these to model AAC alongside students!
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
                if "CORE" in c.get('fw', []):
                    title_html += '<span class="core-badge">CORE</span>'
                if "TWS" in c.get('fw', []):
                    title_html += '<span class="tws-badge">TWS</span>'
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
                            if 'db_id' in c:
                                success, message = delete_custom_card_from_db(c['db_id'])
                                if success:
                                    st.success("Deleted")
                                    st.rerun()
                                else:
                                    st.error(message)
                            else:
                                st.error("Cannot delete - missing database ID")
    else:
        st.info("No cards match your search/filters")

# TAB 2: Create/Manage Custom Cards ----------------------------------------
with tabs[1]:
    st.markdown('<div class="section-card"><h3>Create & Manage Custom Cards</h3></div>', unsafe_allow_html=True)
    
    subtab1, subtab2 = st.tabs(["➕ Create New Card", "📋 Manage Existing Cards"])
    
    # SUBTAB 1: Create New Card
    with subtab1:
        st.markdown("Create custom cards that will be available to all staff in the Card Library.")
        
        # Check if editing existing card
        if st.session_state.vst_editing_card:
            st.info(f"✏️ Editing: {st.session_state.vst_editing_card['ti']}")
            edit_data = st.session_state.vst_editing_card
        else:
            edit_data = None
        
        col1, col2 = st.columns(2)
        
        with col1:
            custom_title = st.text_input("Card Title (Main Text)", 
                                         value=edit_data['ti'] if edit_data else "",
                                         placeholder="e.g., I need a drink", 
                                         key="custom_title")
            
            custom_subtitle = st.text_input("Card Subtitle (Small Text)", 
                                           value=edit_data['sub'] if edit_data else "",
                                           placeholder="e.g., I want water", 
                                           key="custom_subtitle")
            
            custom_symbol = st.text_input("ARASAAC Symbol Keyword", 
                                         value=edit_data['symbol_key'] if edit_data else "",
                                         placeholder="e.g., water", 
                                         key="custom_symbol")
            
            custom_category = st.selectbox("Category", 
                                          options=["regulation","communication","actions","social","places","activities"],
                                          index=["regulation","communication","actions","social","places","activities"].index(edit_data['cat']) if edit_data else 0,
                                          key="custom_category")
            
            custom_created_by = st.text_input("Your name (optional)", 
                                             placeholder="e.g., Candice",
                                             key="custom_created_by")
        
        with col2:
            custom_color = st.color_picker("Card Border Color", 
                                          value=edit_data['color'] if edit_data else TEAL, 
                                          key="custom_color")
            
            custom_frameworks = st.multiselect("Frameworks", 
                                              options=list(FW_DETAILS.keys()),
                                              default=edit_data['fw'] if edit_data else ["AAC"],
                                              key="custom_frameworks")
            
            st.markdown("**Preview Symbol:**")
            if custom_symbol:
                preview_symbol_url = get_arasaac_symbol_url(custom_symbol)
                if preview_symbol_url:
                    st.image(preview_symbol_url, width=100)
                else:
                    st.warning("No symbol found - try different keyword")
        
        # Buttons
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        
        with col_btn1:
            if edit_data:
                if st.button("💾 Save Changes", type="primary", use_container_width=True, key="save_edit"):
                    if custom_title and custom_symbol:
                        updated_card = {
                            'cat': custom_category,
                            'color': custom_color,
                            'symbol_key': custom_symbol,
                            'ti': custom_title,
                            'sub': custom_subtitle,
                            'fw': custom_frameworks
                        }
                        success, message = update_custom_card_in_db(edit_data['db_id'], updated_card)
                        if success:
                            st.success(message)
                            st.session_state.vst_editing_card = None
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Enter title and symbol keyword")
            else:
                if st.button("➕ Save to Library", type="primary", use_container_width=True, key="save_new"):
                    if custom_title and custom_symbol:
                        new_card = {
                            'id': f"custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            'cat': custom_category,
                            'color': custom_color,
                            'symbol_key': custom_symbol,
                            'ti': custom_title,
                            'sub': custom_subtitle,
                            'fw': custom_frameworks,
                            'custom': True,
                            'created_by': custom_created_by if custom_created_by else 'Staff'
                        }
                        success, message = save_custom_card_to_db(new_card)
                        if success:
                            st.success(f"✅ {message}")
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Enter title and symbol keyword")
        
        with col_btn2:
            if edit_data and st.button("❌ Cancel Edit", use_container_width=True, key="cancel_edit"):
                st.session_state.vst_editing_card = None
                st.rerun()
        
        with col_btn3:
            pass  # Empty for layout
    
    # SUBTAB 2: Manage Existing Cards
    with subtab2:
        st.markdown("**All Custom Cards** - Edit or delete cards created by staff")
        
        if st.session_state.vst_custom_cards:
            st.markdown(f"*{len(st.session_state.vst_custom_cards)} custom cards in library*")
            
            # Refresh button
            if st.button("🔄 Refresh List", key="refresh_custom"):
                load_custom_cards_from_db.clear()
                st.session_state.vst_custom_cards = load_custom_cards_from_db()
                st.rerun()
            
            st.divider()
            
            # Display all custom cards
            for i, card in enumerate(st.session_state.vst_custom_cards):
                col_preview, col_info, col_actions = st.columns([1, 3, 2])
                
                with col_preview:
                    symbol_url = get_arasaac_symbol_url(card['symbol_key'])
                    if symbol_url:
                        st.image(symbol_url, width=80)
                
                with col_info:
                    st.markdown(f"**{card['ti']}** <span class='custom-badge'>CUSTOM</span>", unsafe_allow_html=True)
                    st.caption(f"{card['sub']}")
                    st.caption(f"📁 {card['cat']} • 🏷️ {', '.join(card['fw'])}")
                    st.caption(f"👤 Created by: {card.get('created_by', 'Unknown')} • 📅 {card.get('created_at', '')[:10]}")
                
                with col_actions:
                    col_edit, col_del = st.columns(2)
                    with col_edit:
                        if st.button("✏️ Edit", key=f"edit_custom_{i}", use_container_width=True):
                            st.session_state.vst_editing_card = card
                            st.rerun()
                    with col_del:
                        if st.button("🗑️ Delete", key=f"del_custom_db_{i}", use_container_width=True):
                            success, message = delete_custom_card_from_db(card['db_id'])
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                
                st.divider()
        else:
            st.info("No custom cards yet. Create one in the 'Create New Card' tab!")

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
    
    if st.button("➕ Add to Queue", type="primary", use_container_width=True, key="add_firstthen"):
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
    
    if st.button("➕ Add to Queue", type="primary", use_container_width=True, key="add_schedule"):
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
    
    if st.button("➕ Add to Queue", type="primary", use_container_width=True, key="add_commboard"):
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
        
        if st.button("➕ Add to Queue", use_container_width=True, key="add_zones"):
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
        
        if st.button("➕ Add to Queue", use_container_width=True, key="add_fivepoint"):
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
        
        if st.button("➕ Add to Queue", use_container_width=True, key="add_feelings"):
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
        
        if st.button("➕ Add to Queue", use_container_width=True, key="add_calmdown"):
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
    
    if st.button("➕ Add to Queue", type="primary", use_container_width=True, key="add_script"):
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
            
            if st.button("🗑️ Clear All", use_container_width=True, key="clear_all_queue"):
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
                    # Generate HTML for just this item
                    selected_item = st.session_state.vst_print_queue[st.session_state.vst_selected_item_index]
                    html_single = generate_print_html([selected_item])
                    
                    st.download_button("⬇️ This Item", 
                                     data=html_single, 
                                     file_name=f"visual_support_item_{st.session_state.vst_selected_item_index + 1}.html",
                                     mime="text/html", 
                                     type="primary", 
                                     use_container_width=True, 
                                     key="download_one")
                with col_all:
                    # Generate HTML for all items
                    html_all = generate_print_html(st.session_state.vst_print_queue)
                    
                    st.download_button("⬇️ All Items", 
                                     data=html_all, 
                                     file_name="visual_supports_all.html",
                                     mime="text/html", 
                                     use_container_width=True, 
                                     key="download_all")
                
                # Print instructions
                st.markdown("""
                <div class="aac-note">
                    <strong>📄 How to Print:</strong><br>
                    1. Open downloaded HTML file in Chrome or Edge<br>
                    2. Press Ctrl+P (Windows) or Cmd+P (Mac)<br>
                    3. Set margins to <strong>None</strong> or <strong>Minimum</strong><br>
                    4. Enable <strong>Background graphics</strong><br>
                    5. Print or Save as PDF
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("👈 Select item to adjust")
