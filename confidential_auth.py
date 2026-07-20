"""
confidential_auth.py
────────────────────
Single shared password gate for the CLC-LBU portal's confidential
(leadership-only) section.

Pages protected by this gate: Leadership, PDP Builder, LC Meeting Summariser.

How it works
------------
• ONE shared password, read from the CONFIDENTIAL_PASSWORD secret / env var.
  (Falls back to ADMIN_PASSWORD, then to a placeholder, so nothing locks out
  if you haven't set the secret yet — but you SHOULD set CONFIDENTIAL_PASSWORD
  to a new value known only to leadership.)
• ONE shared session flag (clc_confidential_ok): entering the password on any
  confidential page unlocks all of them for that browser session.
• Fully self-contained — depends only on streamlit + os, so it drops into any
  page regardless of whether that page uses theme.py / auth.py.

Usage (top of each confidential page, just after st.set_page_config / theme):
    from confidential_auth import require_confidential_auth
    require_confidential_auth("CLC Leadership", "👔")
"""

import os
import streamlit as st

SESSION_KEY = "clc_confidential_ok"
TEAL = "#1A7A7A"
AMBER = "#C8760A"


def _get_confidential_password():
    """Resolve the shared password from secrets, then env vars, with fallbacks."""
    for name in ("CONFIDENTIAL_PASSWORD", "ADMIN_PASSWORD"):
        val = ""
        try:
            val = st.secrets.get(name, "")
        except Exception:
            val = ""
        if not val:
            val = os.environ.get(name, "")
        if val:
            return val
    # Last-resort fallback — confidential/admin tools only.
    # Set CONFIDENTIAL_PASSWORD in Render/secrets to override without a code change.
    return "secret2026"


def is_confidential_unlocked():
    """True if the confidential section has been unlocked this session."""
    return st.session_state.get(SESSION_KEY, False)


def require_confidential_auth(title="Confidential Area",
                              icon="🔒",
                              subtitle="Cowandilla Learning Centre — LBU Leadership"):
    """
    Stop the page and show a password wall unless the confidential section has
    already been unlocked this session. Call once, near the top of the page.
    Returns True when unlocked (otherwise the page is halted via st.stop()).
    """
    if is_confidential_unlocked():
        return True

    st.markdown(f"""
    <div style="max-width:440px;margin:4rem auto 1.5rem;text-align:center;">
      <div style="background:linear-gradient(135deg,{TEAL},#0f5f5f);color:white;
                  border-radius:14px;padding:1.6rem;box-shadow:0 4px 14px rgba(0,0,0,0.12);">
        <div style="font-size:2.6rem;">{icon}</div>
        <h2 style="margin:0.5rem 0 0;font-size:1.3rem;font-weight:700;">{title}</h2>
        <p style="margin:0.4rem 0 0;opacity:0.75;font-size:0.85rem;">{subtitle}</p>
        <div style="margin-top:0.9rem;font-size:0.78rem;background:rgba(255,255,255,0.12);
                    border-radius:8px;padding:0.45rem 0.7rem;display:inline-block;">
          🔒 Confidential — authorised leadership access only
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        pwd = st.text_input("Enter confidential password", type="password",
                            key="confidential_pwd")
        if st.button("🔓 Unlock", key="confidential_login_btn",
                     type="primary", use_container_width=True):
            if pwd and pwd == _get_confidential_password():
                st.session_state[SESSION_KEY] = True
                st.rerun()
            else:
                st.error("🚫 Incorrect password. This area is for CLC Leadership only.")
    st.stop()
    return False


def confidential_logout_button(location="sidebar", label="🔒 Lock confidential area"):
    """Optional: re-lock the confidential section for this session."""
    container = st.sidebar if location == "sidebar" else st
    if container.button(label, key="confidential_logout_btn"):
        st.session_state[SESSION_KEY] = False
        st.rerun()
