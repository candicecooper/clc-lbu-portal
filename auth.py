"""
auth.py — CLC LBU Shared Authentication Module
Drop this file into the root of your repo.
Import and call require_auth() at the top of any page that needs protecting.

Usage:
    from auth import require_auth
    require_auth()

Secrets required in .streamlit/secrets.toml:
    APP_PASSWORD = "your-shared-password"
    # Optional — comma-separated staff names shown in dropdown:
    STAFF_NAMES  = "Alice,Bob,Candice,Dave"
"""

import streamlit as st
import time
from datetime import datetime

TEAL      = "#1A7A7A"
TEAL_DARK = "#0f5252"
AMBER     = "#C8760A"
MAX_ATTEMPTS  = 5
LOCKOUT_SECS  = 300  # 5 minutes


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


def _is_locked() -> bool:
    return time.time() < st.session_state.locked_until


def _remaining_lockout() -> int:
    return max(0, int(st.session_state.locked_until - time.time()))


def require_auth(app_title: str = "CLC LBU", app_icon: str = "🔒"):
    """
    Call at the top of any Streamlit page.
    Blocks rendering and shows login screen until authenticated.
    Once authenticated, session persists until browser tab closes.
    """
    _init_auth_state()

    if st.session_state.authenticated:
        return  # already in — carry on

    # ── Page chrome ───────────────────────────────────────────────
    st.markdown(f"""
    <style>
      .block-container {{ max-width: 420px; padding-top: 3rem; }}
      .login-header {{ text-align: center; margin-bottom: 2rem; }}
      .login-icon {{ font-size: 48px; margin-bottom: 8px; }}
      .login-title {{ font-size: 22px; font-weight: 700; color: {TEAL}; margin-bottom: 2px; }}
      .login-sub {{ font-size: 13px; color: #888; }}
      .lockout-box {{ background: #fce8e8; border: 1px solid #f0b0b0; border-radius: 8px;
                      padding: 12px 16px; font-size: 13px; color: #a32d2d; text-align: center; }}
      .attempt-note {{ font-size: 12px; color: #C8760A; text-align: center; margin-top: 4px; }}
      div[data-testid="stForm"] {{ border: none; padding: 0; }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="login-header">
      <div class="login-icon">{app_icon}</div>
      <div class="login-title">{app_title}</div>
      <div class="login-sub">Cowandilla Learning Centre — LBU Staff Portal</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Lockout check ─────────────────────────────────────────────
    if _is_locked():
        mins, secs = divmod(_remaining_lockout(), 60)
        st.markdown(f"""
        <div class="lockout-box">
          🔒 Too many incorrect attempts.<br>
          Please wait <strong>{mins}:{secs:02d}</strong> before trying again.
        </div>
        """, unsafe_allow_html=True)
        time.sleep(1)
        st.rerun()
        return

    # ── Login form ────────────────────────────────────────────────
    # Staff name: dropdown if STAFF_NAMES secret exists, else free text
    staff_names_raw = st.secrets.get("STAFF_NAMES", "")
    staff_list = [s.strip() for s in staff_names_raw.split(",") if s.strip()]

    with st.form("login_form", clear_on_submit=False):
        if staff_list:
            name_input = st.selectbox("Your name", ["— select —"] + staff_list)
        else:
            name_input = st.text_input("Your name", placeholder="Enter your name")

        password_input = st.text_input("Password", type="password",
                                        placeholder="Staff password")

        submitted = st.form_submit_button("Sign in", use_container_width=True,
                                           type="primary")

    if submitted:
        correct_pw = st.secrets.get("APP_PASSWORD", "")
        name_ok    = (name_input not in ("", "— select —"))
        pw_ok      = (password_input == correct_pw)

        if not name_ok:
            st.warning("Please enter or select your name.")
        elif not pw_ok:
            st.session_state.login_attempts += 1
            remaining = MAX_ATTEMPTS - st.session_state.login_attempts
            if remaining <= 0:
                st.session_state.locked_until = time.time() + LOCKOUT_SECS
                st.session_state.login_attempts = 0
                st.error(f"Too many incorrect attempts. Locked for {LOCKOUT_SECS // 60} minutes.")
            else:
                st.error(f"Incorrect password.")
                if remaining <= 2:
                    st.markdown(
                        f'<p class="attempt-note">{remaining} attempt{"s" if remaining > 1 else ""} remaining before lockout.</p>',
                        unsafe_allow_html=True,
                    )
            st.rerun()
        else:
            # ✅ Success
            st.session_state.authenticated  = True
            st.session_state.staff_name     = name_input if name_ok else "Staff"
            st.session_state.login_attempts = 0
            st.rerun()

    # Block all further rendering until authenticated
    st.stop()


def logout_button(location="sidebar"):
    """
    Render a logout button. Call anywhere after require_auth().
    location: "sidebar" or "inline"
    """
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
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()


def get_staff_name() -> str:
    """Return the logged-in staff member's name."""
    return st.session_state.get("staff_name", "Staff")

