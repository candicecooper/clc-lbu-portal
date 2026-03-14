import streamlit as st

# ── CLC Brand Colours ─────────────────────────────────────────────
TEAL        = "#1A7A7A"
TEAL_LIGHT  = "#e8f2f2"
TEAL_DARK   = "#145f5f"
AMBER       = "#C8760A"
AMBER_LIGHT = "#fdf3e3"

def apply_clc_theme():
    """Call once at the top of every page to apply CLC brand styling."""
    st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    * { font-family: 'Inter', sans-serif; }

    /* ── Background ── */
    .stApp { background: #f0f4f4 !important; }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: #1A7A7A !important;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    [data-testid="stSidebar"] a:hover {
        background: rgba(255,255,255,0.15) !important;
        border-radius: 6px !important;
    }

    /* ── Top header bar ── */
    header[data-testid="stHeader"] {
        background: white !important;
        border-bottom: 3px solid #1A7A7A !important;
    }

    /* ── Primary buttons ── */
    button[kind="primary"], .stButton>button[kind="primary"] {
        background: #1A7A7A !important; color: white !important;
        border: none !important; border-radius: 8px !important;
        padding: 0.55rem 1.4rem !important; font-weight: 600 !important;
        letter-spacing: 0.02em !important;
        box-shadow: 0 2px 6px rgba(26,122,122,0.25) !important;
        transition: all 0.2s ease !important;
    }
    button[kind="primary"]:hover {
        background: #145f5f !important;
        box-shadow: 0 4px 12px rgba(26,122,122,0.35) !important;
        transform: translateY(-1px) !important;
    }

    /* ── Secondary buttons ── */
    .stButton>button {
        background: #2d4a4a !important; color: white !important;
        border: none !important; border-radius: 8px !important;
        padding: 0.5rem 1.2rem !important; font-weight: 500 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12) !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button:hover {
        background: #1A7A7A !important;
        transform: translateY(-1px) !important;
    }

    /* ── Cards / containers ── */
    [data-testid="stVerticalBlock"] > div[style*="border"] {
        background: white !important; border-radius: 12px !important;
        padding: 1.5rem !important;
        box-shadow: 0 1px 4px rgba(26,122,122,0.08) !important;
        border: 1px solid #d0e8e8 !important;
    }

    /* ── Metrics ── */
    [data-testid="stMetricValue"] {
        font-size: 2rem !important; font-weight: 700 !important; color: #1A7A7A !important;
    }
    [data-testid="stMetricLabel"] {
        color: #5a8a8a !important; font-weight: 600 !important; font-size: 0.8rem !important;
        text-transform: uppercase !important; letter-spacing: 0.06em !important;
    }

    /* ── Inputs ── */
    .stTextInput>div>div>input, .stSelectbox>div>div,
    .stTextArea>div>div>textarea, .stNumberInput>div>div>input,
    .stDateInput>div>div>input, .stTimeInput>div>div>input {
        border: 1.5px solid #b8d8d8 !important; background: white !important;
        color: #1a2e2e !important; font-weight: 400 !important;
        border-radius: 8px !important;
        transition: border-color 0.2s !important;
    }
    .stTextInput>div>div>input:focus {
        border-color: #1A7A7A !important;
        box-shadow: 0 0 0 3px rgba(26,122,122,0.12) !important;
    }

    /* ── Headings ── */
    h1 { color: #1A7A7A !important; font-weight: 700 !important; letter-spacing: -0.02em !important; }
    h2 { color: #1a2e2e !important; font-weight: 700 !important; letter-spacing: -0.01em !important; }
    h3 { color: #1a2e2e !important; font-weight: 600 !important; }
    label { color: #2d4a4a !important; font-weight: 600 !important; font-size: 0.875rem !important; }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        border-bottom: 2px solid #d0e8e8 !important;
        gap: 0.25rem !important;
    }
    .stTabs [data-baseweb="tab"] {
        color: #5a8a8a !important; font-weight: 500 !important;
        border-radius: 8px 8px 0 0 !important; padding: 0.6rem 1.2rem !important;
    }
    .stTabs [aria-selected="true"] {
        color: #1A7A7A !important; font-weight: 700 !important;
        border-bottom: 3px solid #1A7A7A !important;
        background: rgba(26,122,122,0.06) !important;
    }

    /* ── Dividers ── */
    hr { border-color: #d0e8e8 !important; }

    /* ── Alerts ── */
    .stSuccess { background: #e8f5f0 !important; color: #0d4a30 !important;
                 border-left: 4px solid #1A7A7A !important; border-radius: 0 8px 8px 0 !important; }
    .stInfo    { background: #e8f2f2 !important; color: #1a3a3a !important;
                 border-left: 4px solid #1A7A7A !important; border-radius: 0 8px 8px 0 !important; }
    .stWarning { background: #fdf3e3 !important; color: #6b3a00 !important;
                 border-left: 4px solid #C8760A !important; border-radius: 0 8px 8px 0 !important; }
    .stError   { background: #fdecea !important; color: #5c1a14 !important;
                 border-left: 4px solid #dc2626 !important; border-radius: 0 8px 8px 0 !important; }

    /* ── Expanders ── */
    .streamlit-expanderHeader {
        background: #e8f2f2 !important; border-radius: 8px !important;
        color: #1A7A7A !important; font-weight: 600 !important;
    }

    /* ── Dataframes ── */
    [data-testid="stDataFrame"] thead tr th {
        background: #1A7A7A !important; color: white !important;
    }
</style>
""", unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "", icon: str = ""):
    """Render a consistent CLC-branded page header."""
    st.markdown(f"""
    <div style="border-left: 4px solid #1A7A7A; padding: 0.4rem 0 0.4rem 1rem; margin-bottom: 1.2rem;">
        <p style="margin:0; color:#5a8a8a; font-size:0.78rem; font-weight:600;
                  text-transform:uppercase; letter-spacing:0.07em;">
            {'&#x1F4CA; ' if not icon else icon + ' '}CLC Learning & Behaviour Unit
        </p>
        <h2 style="margin:0.1rem 0 0; color:#1A7A7A !important; font-size:1.5rem;">{title}</h2>
        {f'<p style="margin:0.2rem 0 0; color:#5a8a8a; font-size:0.9rem;">{subtitle}</p>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)


def amber_banner(text: str):
    """Render an amber accent banner — good for section titles."""
    st.markdown(f"""
    <div style="background:#C8760A; color:white; border-radius:8px;
                padding:0.6rem 1rem; margin-bottom:1rem; font-weight:600;">
        {text}
    </div>
    """, unsafe_allow_html=True)


def teal_banner(text: str):
    """Render a teal accent banner."""
    st.markdown(f"""
    <div style="background:#1A7A7A; color:white; border-radius:8px;
                padding:0.6rem 1rem; margin-bottom:1rem; font-weight:600;">
        {text}
    </div>
    """, unsafe_allow_html=True)
