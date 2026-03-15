"""
auth.py — CLC LBU Shared Authentication Module
Authenticates staff via email + password against the Supabase staff table.

Usage:
    from auth import require_auth, logout_button, get_staff_name, is_admin
    require_auth("App Title", "🏫")

Supabase staff table must have columns:
    email, password, name, role (ADM = admin, others = staff)

Secrets required in .streamlit/secrets.toml:
    SUPABASE_URL = "..."
    SUPABASE_KEY = "..."
"""

import streamlit as st
import time
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
from supabase import create_client

TEAL       = "#1A7A7A"
TEAL_DARK  = "#0f5252"
AMBER      = "#C8760A"
MAX_ATTEMPTS  = 5
LOCKOUT_SECS  = 300  # 5 minutes


# ── Supabase connection ───────────────────────────────────────────

@st.cache_resource(ttl=60)
def _get_supabase():
    import os
    try:
        # Try secrets first, fall back to env vars
        try:
            url = st.secrets.get("supabase", {}).get("url") or st.secrets.get("BEHAVIOUR_SUPABASE_URL", "")
            key = st.secrets.get("supabase", {}).get("key") or st.secrets.get("BEHAVIOUR_SUPABASE_KEY", "")
        except Exception:
            url = os.environ.get("BEHAVIOUR_SUPABASE_URL", "")
            key = os.environ.get("BEHAVIOUR_SUPABASE_KEY", "")
        if not url or not key:
            return None
        return create_client(url, key)
    except Exception:
        return None


def _load_staff():
    supabase = _get_supabase()
    if not supabase:
        return []
    try:
        response = supabase.table("staff").select("*").execute()
        return response.data or []
    except Exception:
        return []


def _verify_password(plain: str, stored_hash: str, stored_plain: str) -> bool:
    """Try bcrypt hash first, fall back to plain text comparison."""
    if stored_hash and BCRYPT_AVAILABLE:
        try:
            return bcrypt.checkpw(plain.encode(), stored_hash.encode())
        except Exception:
            pass
    if stored_plain:
        return plain == stored_plain
    return False


def _authenticate(email: str, password: str):
    """
    Returns staff dict if credentials valid, None otherwise.
    """
    # Admin bypass via secrets or env vars
    import os
    try:
        admin_email = st.secrets.get("admin", {}).get("email", "") or os.environ.get("BEHAVIOUR_ADMIN_EMAIL", "")
        admin_password = st.secrets.get("admin", {}).get("password", "") or os.environ.get("BEHAVIOUR_ADMIN_PASSWORD", "")
    except Exception:
        admin_email = os.environ.get("BEHAVIOUR_ADMIN_EMAIL", "")
        admin_password = os.environ.get("BEHAVIOUR_ADMIN_PASSWORD", "")
    if admin_email and email.lower() == admin_email.lower() and password == admin_password:
        return {
            "id": "admin",
            "name": "Admin",
            "email": admin_email,
            "role": "ADM",
        }

    staff_list = _load_staff()
    for s in staff_list:
        if s.get("email", "").lower() == email.lower():
            stored_hash  = s.get("password_hash") or ""
            stored_plain = s.get("password") or ""
            if _verify_password(password, stored_hash, stored_plain):
                return s
    return None


# ── Session state ─────────────────────────────────────────────────

def _init_auth_state():
    defaults = {
        "authenticated":  False,
        "staff_name":     "",
        "staff_email":    "",
        "staff_role":     "",
        "staff_id":       "",
        "login_attempts": 0,
        "locked_until":   0.0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _is_locked() -> bool:
    return time.time() < st.session_state.locked_until


def _remaining_lockout() -> int:
    return max(0, int(st.session_state.locked_until - time.time()))


# ── Public API ────────────────────────────────────────────────────

def require_auth(app_title: str = "CLC LBU", app_icon: str = "🏫"):
    """
    Call at the top of any Streamlit page.
    Blocks rendering until authenticated.
    """
    _init_auth_state()

    if st.session_state.authenticated:
        return

    # ── Login page styling ────────────────────────────────────────
    st.markdown(f"""
    <style>
      .block-container {{ max-width: 440px; padding-top: 3rem; }}
      .login-header {{ text-align: center; margin-bottom: 2rem; }}
      .login-icon {{ font-size: 48px; margin-bottom: 8px; }}
      .login-title {{ font-size: 22px; font-weight: 700; color: {TEAL}; margin-bottom: 2px; }}
      .login-sub {{ font-size: 13px; color: #888; }}
      .lockout-box {{ background: #fce8e8; border: 1px solid #f0b0b0; border-radius: 8px;
                      padding: 12px 16px; font-size: 13px; color: #a32d2d; text-align: center; }}
      .attempt-note {{ font-size: 12px; color: {AMBER}; text-align: center; margin-top: 4px; }}
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

    # ── Login form (no st.form to avoid submit issues) ────────────
    email_input    = st.text_input("Email address",
                                    placeholder="your.name@schools.sa.edu.au",
                                    key="auth_email")
    password_input = st.text_input("Password", type="password",
                                    placeholder="Your password",
                                    key="auth_password")
    submitted = st.button("Sign in", use_container_width=True, type="primary", key="auth_submit")

    st.markdown(
        "<p style='text-align:center; color:#aaa; font-size:0.8rem; margin-top:0.5rem;'>"
        "Contact your admin if you need access</p>",
        unsafe_allow_html=True
    )

    if submitted:
        if not email_input or not password_input:
            st.warning("Please enter your email and password.")
        else:
            # Debug info
            import os
            sb = _get_supabase()
            staff_list = _load_staff()
            with st.expander("🔍 Debug info (remove after fixing)"):
                st.write(f"Supabase connected: {sb is not None}")
                st.write(f"Staff count: {len(staff_list)}")
                st.write(f"Admin email from env: {os.environ.get('BEHAVIOUR_ADMIN_EMAIL', 'NOT SET')}")
                try:
                    st.write(f"Admin email from secrets: {st.secrets.get('admin', {}).get('email', 'NOT SET')}")
                except:
                    st.write("Secrets not accessible")
                if staff_list:
                    st.write(f"First staff email: {staff_list[0].get('email', 'no email field')}")
            staff = _authenticate(email_input.strip(), password_input)
            if staff:
                # Handle both name (single field) and first_name/last_name
                first = staff.get("first_name", "")
                last  = staff.get("last_name", "")
                full_name = f"{first} {last}".strip() if (first or last) else staff.get("name", email_input.split("@")[0].replace(".", " ").title())
                st.session_state.authenticated  = True
                st.session_state.staff_name     = full_name
                st.session_state.staff_email    = email_input.strip()
                st.session_state.staff_role     = staff.get("role", "")
                st.session_state.staff_id       = str(staff.get("id", ""))
                st.session_state.login_attempts = 0
                st.rerun()
            else:
                st.session_state.login_attempts += 1
                remaining = MAX_ATTEMPTS - st.session_state.login_attempts
                if remaining <= 0:
                    st.session_state.locked_until   = time.time() + LOCKOUT_SECS
                    st.session_state.login_attempts = 0
                    st.error(f"Too many incorrect attempts. Locked for {LOCKOUT_SECS // 60} minutes.")
                else:
                    st.error("Incorrect email or password.")
                    if remaining <= 2:
                        st.markdown(
                            f'<p class="attempt-note">{remaining} attempt{"s" if remaining > 1 else ""} remaining before lockout.</p>',
                            unsafe_allow_html=True,
                        )
                st.rerun()

    st.stop()


def require_admin(message: str = "This section requires admin access."):
    """
    Call inside any admin-only section.
    Shows password prompt if not already admin-authenticated.
    """
    if is_admin():
        return True

    admin_pw = st.secrets.get("ADMIN_PASSWORD", "")
    with st.form("admin_auth_form"):
        st.warning(f"🔒 {message}")
        entered = st.text_input("Admin password", type="password")
        if st.form_submit_button("Unlock", type="primary"):
            if entered == admin_pw or entered == st.secrets.get("admin", {}).get("password", ""):
                st.session_state.staff_role = "ADM"
                st.rerun()
            else:
                st.error("Incorrect admin password.")
    st.stop()
    return False


def logout_button(location: str = "sidebar"):
    """Render a logout button."""
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
    for k in ["authenticated", "staff_name", "staff_email", "staff_role",
              "staff_id", "login_attempts", "locked_until"]:
        st.session_state.pop(k, None)
    st.rerun()


def get_staff_name() -> str:
    """Return the logged-in staff member's display name."""
    return st.session_state.get("staff_name", "Staff")


def get_staff_role() -> str:
    """Return the logged-in staff member's role."""
    return st.session_state.get("staff_role", "")


def is_admin() -> bool:
    """Return True if the logged-in user has admin role."""
    return st.session_state.get("staff_role", "") == "ADM"
