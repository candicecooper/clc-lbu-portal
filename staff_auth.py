"""
staff_auth.py
─────────────
Single shared password gate for the CLC-LBU portal's GENERAL staff tools.

Use this on all password-protected tools EXCEPT the confidential/admin
section (Leadership, PDP Builder, LC Meeting Summariser, Document Archive
confidential areas) — those keep using confidential_auth.py.

How it works
------------
• ONE shared staff password, read from the STAFF_PASSWORD secret / env var,
  with a code fallback so nothing hard-locks before setup.
• ONE shared session flag (clc_staff_ok): entering the password on any
  general tool unlocks all of them for that browser session.
• Separate session flag from the confidential gate, so unlocking staff
  tools does NOT unlock the confidential section (and vice versa).
• Fully self-contained — depends only on streamlit + os.

Usage (top of each general tool page, just after st.set_page_config / theme):
    from staff_auth import require_staff_auth
    require_staff_auth("Communication Log", "📒")
"""

import os
import streamlit as st

SESSION_KEY = "clc_staff_ok"
TEAL = "#1A7A7A"
AMBER = "#C8760A"


def _get_staff_password():
    """Resolve the shared staff password from secrets, then env vars."""
    val = ""
    try:
        val = st.secrets.get("STAFF_PASSWORD", "")
    except Exception:
        val = ""
    if not val:
        val = os.environ.get("STAFF_PASSWORD", "")
    if val:
        return val
    # Last-resort fallback — general staff tools only.
    # Set STAFF_PASSWORD in Render/secrets to override without a code change.
    return "clcstaff2026"


def is_staff_unlocked():
    """True if the staff tools have been unlocked this session."""
    return st.session_state.get(SESSION_KEY, False)


def require_staff_auth(title="Staff Tools",
                       icon="🧰",
                       subtitle="Cowandilla Learning Centre — LBU Staff"):
    """
    Stop the page and show a password wall unless the staff tools have
    already been unlocked this session. Call once, near the top of the page.
    Returns True when unlocked (otherwise the page is halted via st.stop()).
    """
    if is_staff_unlocked():
        return True

    st.markdown(f"""
    <div style="max-width:440px;margin:4rem auto 1.5rem;text-align:center;">
      <div style="background:linear-gradient(135deg,{AMBER},#9a5a08);color:white;
                  border-radius:14px;padding:1.6rem;box-shadow:0 4px 14px rgba(0,0,0,0.12);">
        <div style="font-size:2.6rem;">{icon}</div>
        <h2 style="margin:0.5rem 0 0;font-size:1.3rem;font-weight:700;">{title}</h2>
        <p style="margin:0.4rem 0 0;opacity:0.75;font-size:0.85rem;">{subtitle}</p>
        <div style="margin-top:0.9rem;font-size:0.78rem;background:rgba(255,255,255,0.12);
                    border-radius:8px;padding:0.45rem 0.7rem;display:inline-block;">
          🔑 Staff access — enter the staff password
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        pwd = st.text_input("Enter staff password", type="password",
                            key="staff_pwd")
        if st.button("🔓 Unlock", key="staff_login_btn",
                     type="primary", use_container_width=True):
            if pwd and pwd == _get_staff_password():
                st.session_state[SESSION_KEY] = True
                st.rerun()
            else:
                st.error("🚫 Incorrect password. Please check the staff bulletin "
                         "or ask leadership if you're unsure.")
    st.stop()
    return False


def staff_logout_button(location="sidebar", label="🔒 Lock staff tools"):
    """Optional: re-lock the staff tools for this session."""
    container = st.sidebar if location == "sidebar" else st
    if container.button(label, key="staff_logout_btn"):
        st.session_state[SESSION_KEY] = False
        st.rerun()
