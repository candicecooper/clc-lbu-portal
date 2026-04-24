from theme import apply_clc_theme
import streamlit as st
import re
import time
import pandas as pd
from datetime import datetime, date

from database import (
    get_or_create_current_edition, get_edition, get_notices_for_edition,
    get_current_published_edition, get_all_editions,
    publish_edition, sync_to_staff_minutes,
    create_notice, record_acknowledgement, has_acknowledged,
    get_staff_list, get_staff_names, add_staff_member, remove_staff_member,
    set_staff_pin, verify_pin,
)
try:
    from email_utils import send_edition_notification
except ImportError:
    def send_edition_notification(*args, **kwargs):
        return False, "Email not configured"

st.set_page_config(page_title="CLC Staff Bulletin", page_icon="📋",
                   layout="wide", initial_sidebar_state="collapsed")
apply_clc_theme()

# ── Supabase (for notice deletion only) ───────────────────────────────────────
@st.cache_resource
def _get_supabase():
    from supabase import create_client
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def delete_notice(notice_id: str) -> bool:
    try:
        _get_supabase().table("notices").delete().eq("id", notice_id).execute()
        return True
    except:
        return False

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in {
    "staff_name": "", "staff_id": None, "is_admin": False,
    "login_attempts": 0, "view": "bulletin", "viewing_edition_id": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Constants ─────────────────────────────────────────────────────────────────
CAT_LABELS = {
    "action":   "Action Required",
    "whs":      "WHS",
    "policy":   "Policy Update",
    "reminder": "Reminder",
    "info":     "Information",
    "general":  "General",
}
CAT_STYLE = {
    "action":   "background:#fee2e2;color:#991b1b;",
    "whs":      "background:#d1fae5;color:#065f46;",
    "policy":   "background:#dbeafe;color:#1e40af;",
    "reminder": "background:#fef3c7;color:#92400e;",
    "info":     "background:#ede9fe;color:#5b21b6;",
    "general":  "background:#f3f4f6;color:#374151;",
}

def fmt_date(d):
    if not d: return ""
    try:
        return datetime.fromisoformat(str(d).replace("Z", "+00:00")).strftime("%-d %b %Y")
    except:
        return str(d)[:10]

def nav(view, edition_id=None):
    st.session_state.view = view
    if edition_id is not None:
        st.session_state.viewing_edition_id = edition_id
    st.rerun()

# ── Edition-level acknowledgement helpers ─────────────────────────────────────
def has_acked_edition(edition_id, staff_name) -> bool:
    notices = get_notices_for_edition(edition_id)
    if not notices:
        return False
    return all(has_acknowledged(n["id"], staff_name) for n in notices)

def ack_all(edition_id, staff_name):
    for n in get_notices_for_edition(edition_id):
        record_acknowledgement(n["id"], staff_name)

# ══════════════════════════════════════════════════════════════════════════════
# SHARED COMPONENTS
# ══════════════════════════════════════════════════════════════════════════════
def app_header():
    ab = '<span class="admin-badge">Admin</span>' if st.session_state.is_admin else ""
    st.markdown(f"""
    <div class="site-header">
      <div style="display:flex;align-items:center;">
        <div class="site-logo">📋</div>
        <div>
          <div class="site-title">CLC Staff Bulletin</div>
          <div class="site-sub">Cowandilla Learning Centre</div>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:10px;">
        {ab}<div class="user-chip">👤 {st.session_state.staff_name}</div>
      </div>
    </div>""", unsafe_allow_html=True)
    _, so = st.columns([11, 1])
    with so:
        if st.button("Sign out", key="signout"):
            for k in ["staff_name","staff_id","is_admin","login_attempts"]:
                st.session_state[k] = ("" if k=="staff_name" else
                                       None if k=="staff_id" else
                                       False if k=="is_admin" else 0)
            st.rerun()

def nav_bar(active):
    tabs = [("bulletin", "📖 This Week")]
    if st.session_state.is_admin:
        tabs += [("compose", "✏️ Compose & Send"), ("staff", "👥 Staff")]
    tabs.append(("archive", "🗂 Past Bulletins"))
    cols = st.columns(len(tabs))
    for i, (view, label) in enumerate(tabs):
        with cols[i]:
            if st.button(label, key=f"nav_{view}",
                         type="primary" if active == view else "secondary",
                         use_container_width=True):
                nav(view)
    st.write("")

def render_bulletin(edition, show_ack=True):
    """Shared bulletin renderer — used for current week and archive views."""
    notices = get_notices_for_edition(edition["id"])
    acked   = has_acked_edition(edition["id"], st.session_state.staff_name)

    ack_pill = (
        '<span style="background:#d1fae5;color:#065f46;border-radius:20px;padding:3px 12px;font-size:12px;font-weight:700;">✓ Acknowledged</span>'
        if acked else
        '<span style="background:#fef3c7;color:#b45309;border-radius:20px;padding:3px 12px;font-size:12px;font-weight:700;">⚠ Awaiting acknowledgement</span>'
    ) if show_ack else ""

    # Edition header
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,var(--navy),var(--navy-mid));
                border-radius:var(--radius-lg);padding:22px 28px;margin-bottom:24px;">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                  letter-spacing:0.1em;color:rgba(255,255,255,0.5);margin-bottom:6px;">
        📋 CLC Staff Bulletin
      </div>
      <div style="font-size:26px;font-weight:800;color:white;margin-bottom:8px;">
        {edition["week_label"]}
      </div>
      <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
        <span style="font-size:13px;color:rgba(255,255,255,0.6);">
          Sent {fmt_date(edition.get("published_at"))} · {len(notices)} item{"s" if len(notices)!=1 else ""}
        </span>
        {ack_pill}
      </div>
    </div>""", unsafe_allow_html=True)

    if not notices:
        st.info("No items in this bulletin.")
        return

    # Items — styled like labelled emails
    for n in notices:
        cat     = n.get("category", "general")
        label   = CAT_LABELS.get(cat, cat.title())
        style   = CAT_STYLE.get(cat, CAT_STYLE["general"])
        content = re.sub('<[^<]+?>', '', n.get("content", ""))

        st.markdown(f"""
        <div style="background:var(--white);border:1px solid var(--border);
                    border-radius:var(--radius);padding:18px 22px;margin-bottom:10px;
                    border-left:4px solid {'#dc2626' if cat=='action' else '#059669' if cat=='whs' else '#2563eb' if cat=='policy' else '#d97706' if cat=='reminder' else '#7c3aed' if cat=='info' else '#9ca3af'};">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
            <span style="padding:2px 10px;border-radius:20px;font-size:11px;font-weight:700;{style}">{label}</span>
            <span style="font-size:12px;color:var(--ink-faint);">from {n.get('author','Admin')}</span>
          </div>
          <div style="font-size:16px;font-weight:700;color:var(--ink);margin-bottom:8px;">{n['title']}</div>
          <div style="font-size:14px;color:var(--ink);line-height:1.7;white-space:pre-wrap;">{content}</div>
        </div>""", unsafe_allow_html=True)

    # Single acknowledge button at bottom
    if show_ack:
        st.write("")
        if acked:
            st.success("✅ You have acknowledged this bulletin.")
        else:
            if st.button("✓ Mark as Read & Acknowledge", type="primary", use_container_width=True):
                ack_all(edition["id"], st.session_state.staff_name)
                st.success("✅ Acknowledged — thank you!")
                time.sleep(1)
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════════════════════════════
def show_login():
    left, right = st.columns([1.2, 1])
    with left:
        st.markdown("""
        <div class="login-panel-left">
          <div class="login-brand-icon">📋</div>
          <div class="login-brand-title">CLC Staff<br>Bulletin</div>
          <div class="login-brand-sub">Cowandilla Learning Centre — LBU</div>
          <div class="login-info-pills">
            <div class="login-info-pill">
              <div class="lip-icon">📧</div>
              <div class="lip-text"><strong>Weekly bulletin</strong> sent each Wednesday</div>
            </div>
            <div class="login-info-pill">
              <div class="lip-icon">✅</div>
              <div class="lip-text"><strong>Acknowledge receipt</strong> by Thursday COB</div>
            </div>
            <div class="login-info-pill">
              <div class="lip-icon">🗂</div>
              <div class="lip-text"><strong>All bulletins</strong> logged in staff meeting minutes</div>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)
    with right:
        st.markdown("""
        <div class="login-panel-right">
          <div class="login-form-title">Welcome back</div>
          <div class="login-form-sub">Select your name and enter your PIN to access the staff bulletin.</div>
        </div>""", unsafe_allow_html=True)
        staff_names = get_staff_names()
        if not staff_names:
            st.warning("No staff set up yet. Please contact your administrator.")
            return
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        name = st.selectbox("Your name", ["— Select your name —"] + staff_names)
        pin  = st.text_input("PIN", type="password", placeholder="Enter your PIN")
        if st.session_state.login_attempts >= 5:
            st.error("Too many failed attempts. Contact your administrator.")
        elif st.button("Sign In →", use_container_width=True, type="primary"):
            if name == "— Select your name —":
                st.error("Please select your name.")
            elif not pin.strip():
                st.error("Please enter your PIN.")
            else:
                staff = verify_pin(name, pin)
                if staff:
                    st.session_state.staff_name = staff["name"]
                    st.session_state.staff_id   = staff["id"]
                    st.session_state.is_admin   = staff.get("role") == "admin"
                    st.session_state.login_attempts = 0
                    st.rerun()
                else:
                    st.session_state.login_attempts += 1
                    rem = 5 - st.session_state.login_attempts
                    st.error(f"Incorrect PIN. {rem} attempt{'s' if rem!=1 else ''} remaining." if rem > 0 else "Account locked.")
        st.markdown('<div style="text-align:center;margin-top:14px;font-size:12px;color:#9CA3AF;">Forgotten your PIN? Contact your administrator.</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# THIS WEEK'S BULLETIN
# ══════════════════════════════════════════════════════════════════════════════
def show_bulletin():
    app_header()
    nav_bar("bulletin")
    published = get_current_published_edition()
    if not published:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;">
          <div style="font-size:40px;margin-bottom:16px;">📭</div>
          <div style="font-size:18px;font-weight:700;color:var(--ink);margin-bottom:8px;">No bulletin this week yet</div>
          <div style="font-size:14px;color:var(--ink-light);">The weekly bulletin is usually sent on Wednesday morning.</div>
        </div>""", unsafe_allow_html=True)
        return
    render_bulletin(published, show_ack=True)


# ══════════════════════════════════════════════════════════════════════════════
# COMPOSE & SEND  (admin only)
# ══════════════════════════════════════════════════════════════════════════════
def show_compose():
    app_header()
    nav_bar("compose")
    if not st.session_state.is_admin:
        st.error("⛔ Admin access only.")
        return

    edition = get_or_create_current_edition()
    if not edition:
        st.error("Could not load current edition.")
        return

    notices = get_notices_for_edition(edition["id"])
    is_sent = edition.get("status") == "published"

    # Status banner
    if is_sent:
        st.markdown(f"""
        <div style="background:#d1fae5;border:1px solid #6ee7b7;border-radius:var(--radius);
                    padding:14px 20px;margin-bottom:20px;">
          <div style="font-weight:700;color:#065f46;font-size:15px;">✅ {edition['week_label']} — Sent</div>
          <div style="font-size:13px;color:#047857;margin-top:2px;">
            Published {fmt_date(edition.get('published_at'))} · {len(notices)} item{"s" if len(notices)!=1 else ""}
          </div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:var(--amber-light);border:2px solid #F59E0B;border-radius:var(--radius);
                    padding:14px 20px;margin-bottom:20px;">
          <div style="font-weight:700;color:var(--amber);font-size:15px;">✏️ Draft — {edition['week_label']}</div>
          <div style="font-size:13px;color:var(--amber);margin-top:2px;">
            {len(notices)} item{"s" if len(notices)!=1 else ""} · Not sent yet
          </div>
        </div>""", unsafe_allow_html=True)

    # Draft items
    if notices:
        st.markdown("#### Items")
        for n in notices:
            cat   = n.get("category", "general")
            label = CAT_LABELS.get(cat, cat.title())
            style = CAT_STYLE.get(cat, CAT_STYLE["general"])
            preview = re.sub('<[^<]+?>', '', n.get("content", ""))[:120]
            c1, c2 = st.columns([11, 1])
            with c1:
                st.markdown(f"""
                <div style="background:var(--white);border:1px solid var(--border);
                            border-radius:var(--radius);padding:12px 18px;margin-bottom:6px;">
                  <span style="padding:2px 9px;border-radius:20px;font-size:11px;font-weight:700;{style}">{label}</span>
                  <span style="font-size:15px;font-weight:700;color:var(--ink);margin-left:10px;">{n['title']}</span>
                  <div style="font-size:13px;color:var(--ink-light);margin-top:5px;">{preview}{"…" if len(preview)==120 else ""}</div>
                </div>""", unsafe_allow_html=True)
            with c2:
                if not is_sent:
                    st.write("")
                    if st.button("🗑", key=f"del_{n['id']}", help="Remove"):
                        delete_notice(n["id"])
                        st.rerun()

    elif not is_sent:
        st.info("No items yet — add your first item below.")

    st.write("")

    # Add item
    if not is_sent:
        with st.expander("➕ Add Item", expanded=len(notices) == 0):
            with st.form("add_item", clear_on_submit=True):
                cat     = st.selectbox("Category", list(CAT_LABELS.keys()),
                                       format_func=lambda x: CAT_LABELS[x])
                title   = st.text_input("Subject / Title *",
                                        placeholder="e.g. Reminder: Staff PD next Friday")
                content = st.text_area("Body *", height=140,
                                       placeholder="Write your message here…")
                if st.form_submit_button("Add to Bulletin →", type="primary", use_container_width=True):
                    if not title.strip():
                        st.error("Please enter a title.")
                    elif not content.strip():
                        st.error("Please enter a body.")
                    else:
                        create_notice(
                            edition_id=edition["id"], title=title.strip(),
                            content=content.strip(), category=cat,
                            author=st.session_state.staff_name, audience="All Staff",
                            has_actions=False, actions=[],
                            has_poll=False, poll_question="", poll_options=[],
                            has_comments=False, comment_prompt="",
                            uploaded_files=None
                        )
                        st.success("Added ✓")
                        time.sleep(0.3)
                        st.rerun()

        # Send button
        if notices:
            st.markdown("---")
            if not st.session_state.get("confirm_send"):
                if st.button("🚀 Send to All Staff", type="primary", use_container_width=True):
                    st.session_state["confirm_send"] = True
                    st.rerun()
            else:
                staff_list = get_staff_list()
                emails = [s["email"] for s in staff_list if s.get("email")]
                st.warning(f"This will email **{len(emails)} staff member{'s' if len(emails)!=1 else ''}** and log to meeting minutes. Confirm?")
                s1, s2 = st.columns(2)
                with s1:
                    if st.button("✓ Yes, Send Now", type="primary", use_container_width=True):
                        if publish_edition(edition["id"], st.session_state.staff_name):
                            sync_ok, _ = sync_to_staff_minutes(edition["id"])
                            send_edition_notification(
                                edition["week_label"], len(notices), emails,
                                st.secrets.get("APP_URL", "")
                            )
                            st.session_state["confirm_send"] = False
                            st.success(f"✅ Bulletin sent!{' Minutes logged.' if sync_ok else ''}")
                            time.sleep(1.5)
                            st.rerun()
                with s2:
                    if st.button("Cancel", use_container_width=True):
                        st.session_state["confirm_send"] = False
                        st.rerun()

    # Acknowledgement tracker (post-send)
    if is_sent:
        st.markdown("---")
        st.markdown("#### ✅ Acknowledgements")
        staff_list = get_staff_list()
        rows = [{"Staff Member": s["name"],
                 "Acknowledged": "✅ Yes" if has_acked_edition(edition["id"], s["name"]) else "⏳ Pending"}
                for s in staff_list]
        n_acked = sum(1 for r in rows if "Yes" in r["Acknowledged"])
        st.caption(f"{n_acked} of {len(rows)} staff acknowledged")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAST BULLETINS (archive)
# ══════════════════════════════════════════════════════════════════════════════
def show_archive():
    app_header()
    nav_bar("archive")
    st.markdown('<div class="page-heading">Past <span class="accent">Bulletins</span></div>',
                unsafe_allow_html=True)
    editions = [e for e in get_all_editions() if e.get("status") == "published"]
    if not editions:
        st.info("No bulletins sent yet.")
        return
    for ed in editions:
        notices = get_notices_for_edition(ed["id"])
        acked   = has_acked_edition(ed["id"], st.session_state.staff_name)
        c1, c2  = st.columns([5, 1])
        with c1:
            st.markdown(f"""
            <div style="background:var(--white);border:1px solid var(--border);
                        border-radius:var(--radius);padding:14px 20px;margin-bottom:4px;">
              <div style="font-size:15px;font-weight:700;color:var(--ink);">{ed['week_label']}</div>
              <div style="font-size:12px;color:var(--ink-faint);margin-top:3px;">
                Sent {fmt_date(ed.get('published_at'))} · {len(notices)} item{"s" if len(notices)!=1 else ""}
                · {'✅ Acknowledged' if acked else '⏳ Pending'}
              </div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.write("")
            if st.button("View →", key=f"arch_{ed['id']}", use_container_width=True):
                nav("archive_week", edition_id=ed["id"])
        st.write("")

def show_archive_week():
    app_header()
    ed = get_edition(st.session_state.viewing_edition_id)
    if not ed:
        nav("archive")
        return
    if st.button("← Back to Past Bulletins"):
        nav("archive")
    render_bulletin(ed, show_ack=True)


# ══════════════════════════════════════════════════════════════════════════════
# STAFF MANAGEMENT  (admin only)
# ══════════════════════════════════════════════════════════════════════════════
def show_staff():
    app_header()
    nav_bar("staff")
    if not st.session_state.is_admin:
        st.error("⛔ Admin access only.")
        return
    st.markdown('<div class="page-heading">Staff <span class="accent">Management</span></div>',
                unsafe_allow_html=True)
    staff = get_staff_list()

    with st.expander("➕ Add New Staff Member", expanded=len(staff) == 0):
        with st.form("add_staff"):
            c1, c2 = st.columns(2)
            with c1:
                nn = st.text_input("Full Name *")
                nr = st.selectbox("Role", ["staff", "admin"])
            with c2:
                ne = st.text_input("School Email *")
                np = st.text_input("Initial PIN *", type="password", help="Min 4 characters")
            if st.form_submit_button("Add Staff Member", type="primary"):
                if not nn.strip():
                    st.error("Name required.")
                elif not ne.strip() or "@" not in ne:
                    st.error("Valid email required.")
                elif len(np.strip()) < 4:
                    st.error("PIN must be at least 4 characters.")
                else:
                    if add_staff_member(nn.strip(), ne.strip(), np.strip(), nr):
                        st.success(f"✅ {nn} added.")
                        time.sleep(0.8)
                        st.rerun()

    st.write("")
    st.markdown(f"### Active Staff ({len(staff)})")
    if not staff:
        st.info("No staff added yet.")
        return

    for s in staff:
        c1, c2, c3, c4 = st.columns([3, 3, 1, 1])
        with c1:
            rb = '<span class="badge badge-policy" style="margin-left:6px">Admin</span>' if s.get("role") == "admin" else ""
            st.markdown(f'<span style="font-weight:600;font-size:14px">{s["name"]}</span>{rb}',
                        unsafe_allow_html=True)
        with c2:
            st.markdown(f'<span style="color:var(--ink-faint);font-size:13px">{s["email"]}</span>',
                        unsafe_allow_html=True)
        with c3:
            if st.button("Reset PIN", key=f"reset_{s['id']}"):
                st.session_state[f"resetting_{s['id']}"] = True
        with c4:
            if st.button("Remove", key=f"rm_{s['id']}"):
                st.session_state[f"confirm_remove_{s['id']}"] = True

        if st.session_state.get(f"confirm_remove_{s['id']}"):
            st.warning(f"Remove **{s['name']}**? Their history is kept.")
            rc1, rc2 = st.columns(2)
            with rc1:
                if st.button("Yes, remove", key=f"crm_{s['id']}", type="primary"):
                    remove_staff_member(s["id"])
                    st.session_state.pop(f"confirm_remove_{s['id']}", None)
                    st.rerun()
            with rc2:
                if st.button("Cancel", key=f"cncrm_{s['id']}"):
                    st.session_state.pop(f"confirm_remove_{s['id']}", None)
                    st.rerun()

        if st.session_state.get(f"resetting_{s['id']}"):
            with st.form(f"pf_{s['id']}"):
                np2 = st.text_input(f"New PIN for {s['name']}", type="password")
                pf1, pf2 = st.columns(2)
                with pf1:
                    if st.form_submit_button("Set PIN", type="primary"):
                        if len(np2.strip()) < 4:
                            st.error("Min 4 characters.")
                        else:
                            set_staff_pin(s["id"], np2.strip())
                            st.success(f"✅ PIN updated for {s['name']}.")
                            st.session_state.pop(f"resetting_{s['id']}", None)
                            time.sleep(0.8)
                            st.rerun()
                with pf2:
                    if st.form_submit_button("Cancel"):
                        st.session_state.pop(f"resetting_{s['id']}", None)
                        st.rerun()
        st.divider()

    st.markdown("---\n### 🔑 Change Your Own PIN")
    with st.form("own_pin"):
        op1, op2 = st.columns(2)
        with op1:
            cur_pin = st.text_input("Current PIN", type="password")
        with op2:
            new_pin = st.text_input("New PIN", type="password")
        if st.form_submit_button("Update My PIN"):
            if not verify_pin(st.session_state.staff_name, cur_pin):
                st.error("Current PIN is incorrect.")
            elif len(new_pin.strip()) < 4:
                st.error("New PIN must be at least 4 characters.")
            else:
                if set_staff_pin(st.session_state.staff_id, new_pin.strip()):
                    st.success("✅ PIN updated.")


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.staff_name:
    show_login()
else:
    v = st.session_state.view
    if   v == "bulletin":     show_bulletin()
    elif v == "compose":      show_compose()
    elif v == "archive":      show_archive()
    elif v == "archive_week": show_archive_week()
    elif v == "staff":        show_staff()
    else:                     show_bulletin()
