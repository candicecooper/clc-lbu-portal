"""
auth.py — CLC LBU Shared Authentication
Simple name dropdown + shared password for portal apps.
"""

import streamlit as st
import time

TEAL  = "#1A7A7A"
AMBER = "#C8760A"
MAX_ATTEMPTS = 5
LOCKOUT_SECS = 300


def _init_auth_state():
    defaults = {
        "authenticated": False,
        "staff_name":    "",
        "login_attempts": 0,
        "locked_until":  0.0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _is_locked():
    return time.time() < st.session_state.locked_until


def require_auth(app_title="CLC LBU", app_icon="🏫"):
    _init_auth_state()

    if st.session_state.authenticated:
        return

    st.markdown(f"""
    <style>
      .block-container {{ max-width: 440px; padding-top: 3rem; }}
      .login-header {{ text-align: center; margin-bottom: 2rem; }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="text-align:center; padding: 2rem 0 1rem;">
      <div style="font-size:3rem;">{app_icon}</div>
      <h2 style="color:{TEAL}; margin:0.5rem 0 0.25rem;">{app_title}</h2>
      <p style="color:#888; font-size:0.85rem;">Cowandilla Learning Centre — LBU Staff Portal</p>
    </div>
    """, unsafe_allow_html=True)

    if _is_locked():
        remaining = max(0, int(st.session_state.locked_until - time.time()))
        mins, secs = divmod(remaining, 60)
        st.error(f"🔒 Too many attempts. Try again in {mins}:{secs:02d}")
        time.sleep(1)
        st.rerun()
        return

    # Get staff list from secrets
    import os
    try:
        staff_names_raw = st.secrets.get("STAFF_NAMES", "")
    except Exception:
        staff_names_raw = os.environ.get("STAFF_NAMES", "")
    
    staff_list = [s.strip() for s in staff_names_raw.split(",") if s.strip()]

    if staff_list:
        name_input = st.selectbox("Your name", ["— select —"] + staff_list, key="auth_name")
    else:
        name_input = st.text_input("Your name", placeholder="Enter your name", key="auth_name")

    # Get staff password - with fallback
    try:
        correct_pw = st.secrets.get("APP_PASSWORD", "")
    except Exception:
        correct_pw = os.environ.get("APP_PASSWORD", "")
    
    # Emergency fallback if no password is set
    if not correct_pw:
        correct_pw = "clcstaff2026"

    password_input = st.text_input("Password", type="password", placeholder="Staff password", key="auth_password")
    
    if st.button("Sign in", type="primary", use_container_width=True, key="auth_submit"):
        name_ok = name_input not in ("", "— select —")
        pw_ok   = (password_input == correct_pw) if correct_pw else False

        if not name_ok:
            st.warning("Please select or enter your name.")
        elif not pw_ok:
            st.session_state.login_attempts += 1
            remaining = MAX_ATTEMPTS - st.session_state.login_attempts
            if remaining <= 0:
                st.session_state.locked_until = time.time() + LOCKOUT_SECS
                st.session_state.login_attempts = 0
                st.error("Too many incorrect attempts.")
            else:
                st.error(f"Incorrect password. {remaining} attempt(s) remaining.")
        else:
            st.session_state.authenticated = True
            st.session_state.staff_name    = name_input
            st.session_state.login_attempts = 0
            st.rerun()

    st.markdown("<p style='text-align:center;color:#aaa;font-size:0.8rem;margin-top:0.5rem;'>Contact your admin if you need access</p>", unsafe_allow_html=True)
    st.stop()


def logout_button(location="sidebar"):
    if not st.session_state.get("authenticated"):
        return
    label = f"👋 Sign out ({st.session_state.get('staff_name', 'Staff')})"
    if location == "sidebar":
        with st.sidebar:
            st.markdown("---")
            if st.button(label, use_container_width=True):
                _do_logout()
    else:
        if st.button(label):
            _do_logout()


def _do_logout():
    for k in ["authenticated", "staff_name", "login_attempts", "locked_until"]:
        st.session_state.pop(k, None)
    st.rerun()


def get_staff_name():
    return st.session_state.get("staff_name", "Staff")


def get_staff_role():
    return st.session_state.get("staff_role", "")


def is_admin():
    return st.session_state.get("staff_role", "") == "ADM"


def require_admin(message="This section requires admin access."):
    import os
    try:
        admin_pw = st.secrets.get("ADMIN_PASSWORD", "")
    except Exception:
        admin_pw = os.environ.get("ADMIN_PASSWORD", "")
    
    # Emergency fallback
    if not admin_pw:
        admin_pw = "Admin123!"
    
    if st.session_state.get("is_portal_admin"):
        return True
    
    st.warning(f"🔒 {message}")
    entered = st.text_input("Admin password", type="password", key="admin_unlock_pw")
    if st.button("Unlock", type="primary", key="admin_unlock_btn"):
        if entered == admin_pw:
            st.session_state.is_portal_admin = True
            st.rerun()
        else:
            st.error("Incorrect admin password.")
    st.stop()
    return False
