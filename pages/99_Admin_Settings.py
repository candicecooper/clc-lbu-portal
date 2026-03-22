import streamlit as st
import requests
import json
from datetime import datetime

st.set_page_config(
    page_title="Portal Admin | CLC LBU",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

from auth import require_auth, logout_button
require_auth("Admin Settings", "⚙️")
logout_button("sidebar")

# ── DESIGN ────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
*,*::before,*::after{box-sizing:border-box}
html,body,[data-testid="stAppViewContainer"]{background:#f0f4f0!important;font-family:'DM Sans',sans-serif}
[data-testid="stHeader"]{display:none}
[data-testid="stSidebar"]{display:none}
#MainMenu,footer,.stDeployButton{display:none}
.main .block-container{padding:0!important;max-width:100%!important}
.top-nav{background:#1a2e44;padding:0 2rem;height:56px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:1000;box-shadow:0 2px 12px rgba(0,0,0,0.2)}
.top-nav-logo{width:32px;height:32px;background:linear-gradient(135deg,#6BBF4E,#4a8f33);border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:800;color:white;font-size:.85rem}
.content-area{padding:1.5rem 2rem 4rem;max-width:1400px;margin:0 auto}
.admin-card{background:white;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.06);overflow:hidden;margin-bottom:1.25rem}
.admin-card-header{padding:.65rem 1rem;display:flex;align-items:center;gap:.5rem}
.admin-card-header.teal{background:#1a7a6e}
.admin-card-header.navy{background:#1a2e44}
.admin-card-header.amber{background:#e8a125}
.admin-card-header.red{background:#b91c1c}
.admin-card-header.slate{background:#6a7f8a}
.admin-card-header h3{font-size:.72rem;font-weight:700;color:white;text-transform:uppercase;letter-spacing:.1em;margin:0}
.admin-card-header.amber h3{color:#1a2e44}
.admin-card-body{padding:1rem}
.app-row{display:flex;align-items:center;gap:.75rem;padding:.6rem .75rem;border-radius:8px;border:1.5px solid #e0e8dc;margin-bottom:.5rem;background:white;transition:box-shadow .15s}
.app-row:hover{box-shadow:0 2px 8px rgba(107,191,78,0.15)}
.app-name{font-weight:700;font-size:.88rem;color:#1a2e44;flex:1}
.app-section{font-size:.68rem;color:#7a9a7a;font-weight:500}
.status-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.status-dot.online{background:#22c55e;box-shadow:0 0 4px rgba(34,197,94,.5)}
.status-dot.offline{background:#ef4444;box-shadow:0 0 4px rgba(239,68,68,.5)}
.status-dot.checking{background:#f59e0b;animation:pulse 1s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.pw-badge{background:#e8f5e1;color:#2d6b1a;border-radius:6px;padding:.2rem .6rem;font-size:.72rem;font-weight:600;font-family:'DM Mono',monospace}
.pw-badge.missing{background:#fee2e2;color:#991b1b}
.pw-badge.supabase{background:#dbeafe;color:#1d4ed8}
.section-divider{font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:#7a9a7a;padding:.5rem 0 .25rem;margin-top:.5rem}
.stTextInput input,.stTextArea textarea{border:1.5px solid #d8e8d4!important;border-radius:8px!important;font-family:'DM Sans',sans-serif!important;font-size:.82rem!important}
.stTextInput input:focus{border-color:#1a7a6e!important;box-shadow:0 0 0 3px rgba(26,122,110,0.12)!important}
.stButton button{border-radius:8px!important;font-weight:600!important;font-size:.85rem!important}
.stButton button[kind="primary"]{background:#1a7a6e!important;border:none!important}
.stButton button[kind="primary"]:hover{background:#155f56!important}
label[data-testid="stWidgetLabel"] p{font-size:.72rem!important;font-weight:600!important;color:#5a7a5a!important;text-transform:uppercase!important;letter-spacing:.06em!important}
</style>
""", unsafe_allow_html=True)

# ── APP REGISTRY ──────────────────────────────────────────────
# Each entry: (page_file, display_name, section, render_path, pw_key)
# render_path: path on the Render app (after base URL)
# pw_key: the st.secrets key that holds the password for that app (None if shared)
BASE_URL = "https://clc-lbu-portal.onrender.com"

APP_REGISTRY = [
    # Section: Daily Operations
    {"id":"bulletin",     "name":"Daily Bulletin",          "section":"Daily Operations",   "path":"/Daily_Bulletin",          "pw_key":"ADMIN_PASSWORD",  "icon":"📋"},
    {"id":"timetable",    "name":"Timetable",               "section":"Daily Operations",   "path":"/Timetable",               "pw_key":"ADMIN_PASSWORD",  "icon":"📅"},
    {"id":"calendar",     "name":"Calendar",                "section":"Daily Operations",   "path":"/Calendar",                "pw_key":"ADMIN_PASSWORD",  "icon":"🗓️"},
    # Section: Staff & HR
    {"id":"staffmeeting", "name":"Digital Staff Meeting",   "section":"Staff & HR",         "path":"/Digital_Staff_Meeting",   "pw_key":"ADMIN_PASSWORD",  "icon":"🤝"},
    {"id":"teammeetings", "name":"Team Meetings",           "section":"Staff & HR",         "path":"/Team_Meetings",           "pw_key":"ADMIN_PASSWORD",  "icon":"👥"},
    {"id":"committees",   "name":"Committees",              "section":"Staff & HR",         "path":"/Committees",              "pw_key":"ADMIN_PASSWORD",  "icon":"🏛️"},
    {"id":"pac",          "name":"PAC Meeting",             "section":"Staff & HR",         "path":"/PAC_Meeting",             "pw_key":"ADMIN_PASSWORD",  "icon":"📋"},
    # Section: Safety & Behaviour
    {"id":"behaviour",    "name":"Behaviour Support",       "section":"Safety & Behaviour", "path":"/Behaviour_Support",       "pw_key":"ADMIN_PASSWORD",  "icon":"🛡️"},
    {"id":"safetyplan",   "name":"Safety & Risk Plan Builder","section":"Safety & Behaviour","path":"/Safety_risk_plan_builder","pw_key":"ADMIN_PASSWORD", "icon":"🔒"},
    # Section: Student Support
    {"id":"sensory",      "name":"Sensory Overview",        "section":"Student Support",    "path":"/Sensory_Overview",        "pw_key":"ADMIN_PASSWORD",  "icon":"🌀"},
    {"id":"sensorypro",   "name":"Sensory Profiles",        "section":"Student Support",    "path":"/Sensory_Profiles",        "pw_key":"ADMIN_PASSWORD",  "icon":"📊"},
    {"id":"engagement",   "name":"Engagement Tracker",      "section":"Student Support",    "path":"/Engagement_Tracker",      "pw_key":"ADMIN_PASSWORD",  "icon":"📈"},
    # Section: Governance
    {"id":"lbupolicy",    "name":"LBU Policy Quiz",         "section":"Governance",         "path":"/LBU_Policy_Quiz",         "pw_key":"ADMIN_PASSWORD",  "icon":"📖"},
]

SECTIONS_ORDER = ["Daily Operations","Staff & HR","Safety & Behaviour","Student Support","Governance"]

# ── SUPABASE HELPERS ──────────────────────────────────────────
def _get_sb():
    import database as db
    return db.get_supabase()

def load_portal_config():
    """Load all portal config rows from Supabase. Returns dict keyed by config_key."""
    try:
        res = _get_sb().table("portal_config").select("*").execute()
        return {r["config_key"]: r for r in (res.data or [])}
    except Exception:
        return {}

def set_portal_config(key, value, label=""):
    """Upsert a config value in Supabase."""
    try:
        sb = _get_sb()
        existing = sb.table("portal_config").select("id").eq("config_key", key).execute()
        if existing.data:
            sb.table("portal_config").update({
                "config_value": value,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("config_key", key).execute()
        else:
            sb.table("portal_config").insert({
                "config_key": key,
                "config_value": value,
                "label": label,
                "updated_at": datetime.utcnow().isoformat()
            }).execute()
        return True
    except Exception as e:
        st.error(f"Could not save config: {e}")
        return False

def get_effective_password(app_id, config):
    """
    Password resolution order:
    1. Supabase portal_config (key: pw_{app_id})
    2. Supabase portal_config (key: pw_shared) — shared portal password
    3. st.secrets ADMIN_PASSWORD
    4. None (not set)
    """
    specific = config.get(f"pw_{app_id}", {}).get("config_value","")
    if specific:
        return specific, "supabase-specific"
    shared = config.get("pw_shared", {}).get("config_value","")
    if shared:
        return shared, "supabase-shared"
    try:
        secret = st.secrets.get("ADMIN_PASSWORD","")
        if secret:
            return "••••••••", "env-var"
    except Exception:
        pass
    return None, "missing"

def check_app_status(path):
    """Quick HEAD request to check if the Render app is responding."""
    try:
        r = requests.head(BASE_URL + path, timeout=8, allow_redirects=True)
        return "online" if r.status_code < 500 else "offline"
    except Exception:
        return "offline"

# ── SESSION STATE ─────────────────────────────────────────────
def init_state():
    defaults = {
        "admin_authed": False,
        "status_cache": {},       # {app_id: "online"|"offline"|"checking"}
        "status_last_check": {},  # {app_id: timestamp}
        "show_pw": {},            # {app_id: bool}
        "config_loaded": False,
        "portal_config": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

MASTER_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "clcstaff2026")

# ── TOP NAV ───────────────────────────────────────────────────
st.markdown("""
<div class="top-nav">
  <div style="display:flex;align-items:center;gap:.75rem;">
    <div class="top-nav-logo">CLC</div>
    <div>
      <div style="font-weight:700;font-size:.95rem;color:white;letter-spacing:.02em;">Portal Admin</div>
      <div style="font-size:.72rem;color:rgba(255,255,255,0.5);letter-spacing:.06em;text-transform:uppercase;">Settings & Management</div>
    </div>
  </div>
  <div>
    <span style="font-size:.75rem;color:rgba(255,255,255,0.5);">⚙️ CLC LBU Portal</span>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="content-area">', unsafe_allow_html=True)

# ── AUTH GATE ─────────────────────────────────────────────────
if not st.session_state.admin_authed:
    st.markdown("""
    <div style="max-width:440px;margin:3rem auto;background:white;border-radius:16px;
    padding:2.5rem;box-shadow:0 8px 32px rgba(0,0,0,0.1);text-align:center;">
    <div style="font-size:2.5rem;margin-bottom:.75rem;">⚙️</div>
    <div style="font-size:1.3rem;font-weight:700;color:#1a2e44;margin-bottom:.4rem;">Portal Admin</div>
    <div style="font-size:.85rem;color:#7a907a;margin-bottom:1.5rem;">
    Enter the master admin password to manage portal settings, app passwords, and view system status.
    </div>
    </div>
    """, unsafe_allow_html=True)
    col_pw, _ = st.columns([1, 1])
    with col_pw:
        pw_in = st.text_input("Master admin password", type="password", placeholder="Enter password…")
        if st.button("🔓 Unlock Admin", type="primary", use_container_width=True):
            if pw_in == MASTER_PASSWORD:
                st.session_state.admin_authed = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    st.stop()

# ── LOAD CONFIG ───────────────────────────────────────────────
if not st.session_state.config_loaded:
    st.session_state.portal_config = load_portal_config()
    st.session_state.config_loaded = True

config = st.session_state.portal_config

# ── PAGE LAYOUT ───────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.25rem;">
  <div>
    <div style="font-size:1.4rem;font-weight:700;color:#1a2e44;">⚙️ Portal Admin</div>
    <div style="font-size:.82rem;color:#7a907a;margin-top:.15rem;">Manage all CLC LBU portal apps — passwords, links, and live status</div>
  </div>
</div>
""", unsafe_allow_html=True)

# Three top-level tabs
tab_apps, tab_passwords, tab_status = st.tabs(["🔗 Apps & Links", "🔑 Password Management", "📡 System Status"])

# ══════════════════════════════════════════════════════════════
# TAB 1: APPS & LINKS
# ══════════════════════════════════════════════════════════════
with tab_apps:
    st.markdown("""
    <div style="background:#e8f5e1;border-radius:10px;padding:.75rem 1rem;margin-bottom:1rem;
    font-size:.82rem;color:#1a2e44;">
    🔗 All portal apps run on <strong>clc-lbu-portal.onrender.com</strong>.
    Click any link to open the app. The Cloudflare portal at <strong>clc-staff.pages.dev</strong>
    links to these same URLs.
    </div>
    """, unsafe_allow_html=True)

    for section in SECTIONS_ORDER:
        apps = [a for a in APP_REGISTRY if a["section"] == section]
        if not apps: continue

        st.markdown(f'<div class="section-divider">{section}</div>', unsafe_allow_html=True)
        for app in apps:
            full_url = BASE_URL + app["path"]
            pw_val, pw_source = get_effective_password(app["id"], config)

            badge_class = {"supabase-specific": "supabase", "supabase-shared": "supabase",
                           "env-var": "", "missing": "missing"}.get(pw_source, "")
            badge_label = {"supabase-specific": "🔑 Custom password",
                           "supabase-shared":   "🔑 Shared password",
                           "env-var":           "🔒 Env variable",
                           "missing":           "⚠️ No password set"}.get(pw_source, "")

            col_icon, col_info, col_pw_badge, col_link = st.columns([0.4, 3, 2, 1.2])
            with col_icon:
                st.markdown(f'<div style="font-size:1.5rem;padding-top:.2rem;">{app["icon"]}</div>', unsafe_allow_html=True)
            with col_info:
                st.markdown(
                    f'<div class="app-name">{app["name"]}</div>'
                    f'<div class="app-section">{section}</div>',
                    unsafe_allow_html=True)
            with col_pw_badge:
                st.markdown(
                    f'<div style="padding-top:.3rem;">'
                    f'<span class="pw-badge {badge_class}">{badge_label}</span>'
                    f'</div>',
                    unsafe_allow_html=True)
            with col_link:
                st.markdown(
                    f'<a href="{full_url}" target="_blank" style="display:inline-block;'
                    f'background:#1a2e44;color:white;font-weight:600;font-size:.75rem;'
                    f'padding:.3rem .75rem;border-radius:7px;text-decoration:none;white-space:nowrap;">'
                    f'Open app →</a>',
                    unsafe_allow_html=True)
            st.markdown('<div style="height:.25rem;"></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Cloudflare portal:** [clc-staff.pages.dev](https://clc-staff.pages.dev) — hosts the staff-facing tiles that link to all of the above")
    st.markdown("**Render service:** [clc-lbu-portal.onrender.com](https://clc-lbu-portal.onrender.com) — the multi-page Streamlit app serving everything")


# ══════════════════════════════════════════════════════════════
# TAB 2: PASSWORD MANAGEMENT
# ══════════════════════════════════════════════════════════════
with tab_passwords:

    st.markdown("""
    <div style="background:#dbeafe;border-radius:10px;padding:.85rem 1rem;margin-bottom:1.25rem;font-size:.82rem;color:#1a2e44;">
    <strong>🔑 How passwords work:</strong><br>
    All apps currently share one password set via the <code>ADMIN_PASSWORD</code> Render environment variable.
    You can override this here — set a <strong>shared portal password</strong> that all apps use,
    or set <strong>per-app passwords</strong> for individual apps. Passwords set here are stored in
    Supabase and take priority over the Render environment variable, so no Render access is needed.
    </div>
    """, unsafe_allow_html=True)

    # ── Shared portal password ────────────────────────────────
    st.markdown('<div class="admin-card"><div class="admin-card-header teal"><h3>🔑 Shared Portal Password</h3></div><div class="admin-card-body">', unsafe_allow_html=True)
    st.markdown("Set one password that applies to **all apps** unless a per-app password is set below.")

    current_shared = config.get("pw_shared", {}).get("config_value","")
    sp1, sp2, sp3 = st.columns([3, 1.5, 1.5])
    with sp1:
        new_shared = st.text_input(
            "New shared password",
            value="",
            type="password",
            placeholder="Enter new shared password…",
            key="new_shared_pw",
            help="Leave blank to keep the current setting"
        )
    with sp2:
        confirm_shared = st.text_input(
            "Confirm password",
            value="",
            type="password",
            placeholder="Re-enter to confirm",
            key="confirm_shared_pw"
        )
    with sp3:
        st.markdown("<div style='padding-top:1.7rem;'>", unsafe_allow_html=True)
        if st.button("💾 Update Shared Password", type="primary", use_container_width=True, key="save_shared_pw"):
            if not new_shared.strip():
                st.warning("Please enter a new password.")
            elif new_shared != confirm_shared:
                st.error("Passwords don't match.")
            elif len(new_shared) < 6:
                st.warning("Password must be at least 6 characters.")
            else:
                if set_portal_config("pw_shared", new_shared, "Shared portal password"):
                    st.session_state.portal_config = load_portal_config()
                    st.session_state.config_loaded = True
                    config = st.session_state.portal_config
                    st.success("✅ Shared password updated — all apps will use this password.")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    if current_shared:
        st.markdown(f'<div style="font-size:.78rem;color:#4a8f33;margin-top:.25rem;">✓ Shared password is currently set in Supabase (last set: {config.get("pw_shared",{}).get("updated_at","—")[:10]})</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="font-size:.78rem;color:#7a907a;margin-top:.25rem;">No shared password set — apps use the Render <code>ADMIN_PASSWORD</code> environment variable</div>', unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

    # ── Per-app passwords ─────────────────────────────────────
    st.markdown('<div class="admin-card"><div class="admin-card-header navy"><h3>🔒 Per-App Passwords</h3></div><div class="admin-card-body">', unsafe_allow_html=True)
    st.markdown("Override individual apps with a unique password. Leave blank to use the shared password above.")

    for section in SECTIONS_ORDER:
        apps = [a for a in APP_REGISTRY if a["section"] == section]
        if not apps: continue
        st.markdown(f'<div class="section-divider">{section}</div>', unsafe_allow_html=True)

        for app in apps:
            pw_key = f"pw_{app['id']}"
            current_app_pw = config.get(pw_key, {}).get("config_value","")
            show_key = f"show_appw_{app['id']}"

            a1, a2, a3, a4, a5 = st.columns([0.3, 2.5, 2, 2, 1.5])
            with a1:
                st.markdown(f'<div style="font-size:1.2rem;padding-top:.4rem;">{app["icon"]}</div>', unsafe_allow_html=True)
            with a2:
                st.markdown(f'<div style="font-weight:600;font-size:.85rem;color:#1a2e44;padding-top:.5rem;">{app["name"]}</div>', unsafe_allow_html=True)
            with a3:
                new_app_pw = st.text_input(
                    "New password",
                    value="",
                    type="password",
                    placeholder="New password…",
                    key=f"appw_{app['id']}_new",
                    label_visibility="collapsed"
                )
            with a4:
                confirm_app_pw = st.text_input(
                    "Confirm",
                    value="",
                    type="password",
                    placeholder="Confirm…",
                    key=f"appw_{app['id']}_confirm",
                    label_visibility="collapsed"
                )
            with a5:
                bcols = st.columns([1, 1])
                with bcols[0]:
                    if st.button("💾", key=f"save_appw_{app['id']}", help=f"Save password for {app['name']}", use_container_width=True):
                        if not new_app_pw.strip():
                            st.warning(f"Enter a password for {app['name']}.")
                        elif new_app_pw != confirm_app_pw:
                            st.error("Passwords don't match.")
                        elif len(new_app_pw) < 6:
                            st.warning("Min 6 characters.")
                        else:
                            if set_portal_config(pw_key, new_app_pw, f"Password for {app['name']}"):
                                st.session_state.portal_config = load_portal_config()
                                config = st.session_state.portal_config
                                st.success(f"✅ Password updated for {app['name']}")
                                st.rerun()
                with bcols[1]:
                    if current_app_pw:
                        if st.button("🗑️", key=f"clear_appw_{app['id']}", help=f"Remove custom password — revert to shared", use_container_width=True):
                            try:
                                _get_sb().table("portal_config").delete().eq("config_key", pw_key).execute()
                                st.session_state.portal_config = load_portal_config()
                                config = st.session_state.portal_config
                                st.success(f"Removed custom password for {app['name']} — now uses shared password.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

            if current_app_pw:
                st.markdown(
                    f'<div style="font-size:.72rem;color:#1d4ed8;margin-bottom:.25rem;padding-left:2.5rem;">'
                    f'✓ Custom password set (updated {config.get(pw_key,{}).get("updated_at","—")[:10]})</div>',
                    unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

    # ── Reset all note ────────────────────────────────────────
    st.markdown("""
    <div style="background:#fff3e0;border-radius:10px;padding:.75rem 1rem;font-size:.8rem;color:#78350f;">
    <strong>⚠️ Render environment variable:</strong> The <code>ADMIN_PASSWORD</code> env var in Render
    is the ultimate fallback if nothing is set in Supabase. To change it permanently at the infrastructure
    level, update it in the Render dashboard under <em>Environment</em> for the clc-lbu-portal service.
    Passwords set here in Supabase take priority and don't require a Render redeploy.
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 3: SYSTEM STATUS
# ══════════════════════════════════════════════════════════════
with tab_status:
    st.markdown("""
    <div style="background:#e8f5e1;border-radius:10px;padding:.75rem 1rem;margin-bottom:1rem;font-size:.82rem;color:#1a2e44;">
    📡 Checks if each app is responding on Render. <strong>Note:</strong> Render free tier spins down after
    15 minutes of inactivity — the first check may take 30–60 seconds to get a response while the
    instance wakes up. If all apps show offline simultaneously, the service is likely cold-starting.
    </div>
    """, unsafe_allow_html=True)

    check_all = st.button("🔄 Check All Apps", type="primary", key="check_all_status")

    for section in SECTIONS_ORDER:
        apps = [a for a in APP_REGISTRY if a["section"] == section]
        if not apps: continue
        st.markdown(f'<div class="section-divider">{section}</div>', unsafe_allow_html=True)

        for app in apps:
            cached = st.session_state.status_cache.get(app["id"])
            last_checked = st.session_state.status_last_check.get(app["id"], "")

            s1, s2, s3, s4 = st.columns([0.3, 3, 1.5, 1.5])
            with s1:
                st.markdown(f'<div style="font-size:1.2rem;padding-top:.3rem;">{app["icon"]}</div>', unsafe_allow_html=True)
            with s2:
                st.markdown(
                    f'<div style="font-weight:600;font-size:.85rem;color:#1a2e44;">{app["name"]}</div>'
                    f'<div style="font-size:.7rem;color:#9ab09a;">{BASE_URL + app["path"]}</div>',
                    unsafe_allow_html=True)
            with s3:
                if check_all or (cached is None):
                    with st.spinner("Checking…"):
                        status = check_app_status(app["path"])
                    st.session_state.status_cache[app["id"]] = status
                    st.session_state.status_last_check[app["id"]] = datetime.now().strftime("%H:%M:%S")
                    cached = status

                if cached == "online":
                    st.markdown('<div style="display:flex;align-items:center;gap:.4rem;padding-top:.2rem;"><div class="status-dot online"></div><span style="font-size:.78rem;color:#15803d;font-weight:600;">Online</span></div>', unsafe_allow_html=True)
                elif cached == "offline":
                    st.markdown('<div style="display:flex;align-items:center;gap:.4rem;padding-top:.2rem;"><div class="status-dot offline"></div><span style="font-size:.78rem;color:#dc2626;font-weight:600;">Offline / sleeping</span></div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div style="display:flex;align-items:center;gap:.4rem;padding-top:.2rem;"><div class="status-dot checking"></div><span style="font-size:.78rem;color:#d97706;font-weight:600;">Not checked</span></div>', unsafe_allow_html=True)

            with s4:
                if st.session_state.status_last_check.get(app["id"]):
                    st.markdown(
                        f'<div style="font-size:.7rem;color:#9ab09a;padding-top:.35rem;">'
                        f'Checked {st.session_state.status_last_check[app["id"]]}</div>',
                        unsafe_allow_html=True)
                else:
                    if st.button("Check", key=f"check_{app['id']}", use_container_width=True):
                        with st.spinner("…"):
                            status = check_app_status(app["path"])
                        st.session_state.status_cache[app["id"]] = status
                        st.session_state.status_last_check[app["id"]] = datetime.now().strftime("%H:%M:%S")
                        st.rerun()

    # ── Render wake-up helper ─────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="admin-card"><div class="admin-card-header slate"><h3>🌅 Wake Up Render</h3></div><div class="admin-card-body">', unsafe_allow_html=True)
    st.markdown("""
    If the portal is sleeping, click below to send a wake-up request. The first response may take
    30–60 seconds. Once awake, the portal stays active as long as staff are using it.
    """)
    if st.button("☀️ Send Wake-Up Request", use_container_width=False, key="wakeup_btn"):
        with st.spinner("Sending wake-up request to Render…"):
            try:
                r = requests.get(BASE_URL, timeout=60)
                if r.status_code < 500:
                    st.success(f"✅ Portal is awake and responding (HTTP {r.status_code}). Staff can now open apps without delay.")
                else:
                    st.warning(f"Portal responded but with status {r.status_code} — may still be warming up.")
            except requests.exceptions.Timeout:
                st.warning("Request timed out after 60 seconds. The service may need more time — try again in 30 seconds.")
            except Exception as e:
                st.error(f"Request failed: {e}")
    st.markdown("</div></div>", unsafe_allow_html=True)


# ── FOOTER ────────────────────────────────────────────────────
st.markdown("""
<div style="margin-top:2rem;padding:1rem;background:white;border-radius:10px;
border:1.5px solid #e0e8dc;font-size:.75rem;color:#7a907a;">
<strong style="color:#1a2e44;">Portal Admin</strong> · Cowandilla Learning Centre LBU ·
Render service: <code>clc-lbu-portal</code> · Supabase: <code>portal_config</code> table
</div>
""", unsafe_allow_html=True)

if st.button("🚪 Lock Admin", type="secondary", key="lock_admin"):
    st.session_state.admin_authed = False
    st.session_state.config_loaded = False
    st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
