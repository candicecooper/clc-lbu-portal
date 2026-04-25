from theme import apply_clc_theme
import streamlit as st
import re
import time
import pandas as pd
from datetime import datetime, date, timedelta

# Staff/auth functions come from database.py — these work fine across all pages
from database import (
    get_staff_names, get_staff_list, add_staff_member, remove_staff_member,
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

# ══════════════════════════════════════════════════════════════════════════════
# SUPABASE — direct client, no database.py
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def get_sb():
    from supabase import create_client
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# ── Auth — delegated to database.py ──────────────────────────────────────────
def db_get_staff_names():
    try:
        return get_staff_names()
    except Exception:
        return []

def db_verify_pin(name, pin):
    try:
        return verify_pin(name, pin)
    except Exception:
        return None

def db_set_pin(staff_id, new_pin):
    try:
        return set_staff_pin(staff_id, new_pin)
    except Exception:
        return False

def db_get_staff_list():
    try:
        return get_staff_list()
    except Exception:
        return []

def db_add_staff(name, email, pin, role):
    try:
        return add_staff_member(name, email, pin, role)
    except Exception:
        return False

def db_remove_staff(staff_id):
    try:
        return remove_staff_member(staff_id)
    except Exception:
        return False

# ── Editions ──────────────────────────────────────────────────────────────────
def db_get_or_create_edition():
    try:
        sb = get_sb()
        today  = date.today()
        monday = today - timedelta(days=today.weekday())
        week_label = monday.strftime("Week of %-d %B %Y")
        res = sb.table("editions").select("*").eq("week_start", monday.isoformat()).execute()
        if res.data:
            return res.data[0]
        ins = sb.table("editions").insert({
            "week_start": monday.isoformat(),
            "week_label": week_label,
            "status": "draft"
        }).execute()
        return ins.data[0] if ins.data else None
    except Exception:
        return None

def db_get_current_published():
    try:
        res = get_sb().table("editions").select("*").eq("status", "published").order("week_start", desc=True).limit(1).execute()
        return res.data[0] if res.data else None
    except Exception:
        return None

def db_get_edition(edition_id):
    try:
        res = get_sb().table("editions").select("*").eq("id", edition_id).execute()
        return res.data[0] if res.data else None
    except Exception:
        return None

def db_get_all_editions():
    try:
        res = get_sb().table("editions").select("*").order("week_start", desc=True).execute()
        return res.data or []
    except Exception:
        return []

def db_publish_edition(edition_id, published_by):
    try:
        get_sb().table("editions").update({
            "status": "published",
            "published_at": datetime.utcnow().isoformat(),
            "published_by": published_by
        }).eq("id", edition_id).execute()
        return True
    except Exception:
        return False

# ── Notices ───────────────────────────────────────────────────────────────────
def db_get_notices(edition_id):
    try:
        res = get_sb().table("notices").select("*").eq("edition_id", edition_id).order("created_at").execute()
        return res.data or []
    except Exception:
        return []

def db_create_notice(edition_id, title, content, category, author):
    try:
        get_sb().table("notices").insert({
            "edition_id": edition_id,
            "title": title,
            "content": content,
            "category": category,
            "author": author,
            "audience": "All Staff",
            "has_actions": False,
            "has_poll": False,
            "has_comments": False,
        }).execute()
        return True
    except Exception:
        return False

def db_delete_notice(notice_id):
    try:
        get_sb().table("notices").delete().eq("id", notice_id).execute()
        return True
    except Exception:
        return False

# ── Acknowledgements ──────────────────────────────────────────────────────────
def db_has_acknowledged(notice_id, staff_name):
    try:
        res = (get_sb().table("responses")
               .select("id")
               .eq("notice_id", notice_id)
               .eq("staff_name", staff_name)
               .not_.is_("acknowledged_at", "null")
               .execute())
        return bool(res.data)
    except Exception:
        return False

def db_acknowledge(notice_id, staff_name):
    try:
        sb  = get_sb()
        now = datetime.utcnow().isoformat()
        existing = sb.table("responses").select("id").eq("notice_id", notice_id).eq("staff_name", staff_name).execute()
        if existing.data:
            sb.table("responses").update({
                "acknowledged_at": now, "read_at": now
            }).eq("notice_id", notice_id).eq("staff_name", staff_name).execute()
        else:
            sb.table("responses").insert({
                "notice_id": notice_id,
                "staff_name": staff_name,
                "read_at": now,
                "acknowledged_at": now
            }).execute()
        return True
    except Exception:
        return False

def db_get_ack_summary(edition_id):
    try:
        notices = db_get_notices(edition_id)
        staff   = db_get_staff_list()
        rows = []
        for s in staff:
            acked = bool(notices) and all(db_has_acknowledged(n["id"], s["name"]) for n in notices)
            rows.append({"Staff Member": s["name"], "Acknowledged": "Yes" if acked else "Pending"})
        return rows
    except Exception:
        return []

# ── Edition-level helpers ─────────────────────────────────────────────────────
def has_acked_edition(edition_id, staff_name):
    notices = db_get_notices(edition_id)
    if not notices:
        return False
    return all(db_has_acknowledged(n["id"], staff_name) for n in notices)

def ack_all(edition_id, staff_name):
    for n in db_get_notices(edition_id):
        db_acknowledge(n["id"], staff_name)

def fmt_date(d):
    if not d:
        return ""
    try:
        return datetime.fromisoformat(str(d).replace("Z", "+00:00")).strftime("%-d %b %Y")
    except Exception:
        return str(d)[:10]

def nav(view, edition_id=None):
    st.session_state.view = view
    if edition_id is not None:
        st.session_state.viewing_edition_id = edition_id
    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
CAT_LABELS = {
    "action":   "Action Required",
    "whs":      "WHS",
    "policy":   "Policy Update",
    "reminder": "Reminder",
    "info":     "Information",
    "general":  "General",
}
CAT_BADGE = {
    "action":   "background:#fee2e2;color:#991b1b;",
    "whs":      "background:#d1fae5;color:#065f46;",
    "policy":   "background:#dbeafe;color:#1e40af;",
    "reminder": "background:#fef3c7;color:#92400e;",
    "info":     "background:#ede9fe;color:#5b21b6;",
    "general":  "background:#f3f4f6;color:#374151;",
}
CAT_BORDER = {
    "action":   "#dc2626",
    "whs":      "#059669",
    "policy":   "#2563eb",
    "reminder": "#d97706",
    "info":     "#7c3aed",
    "general":  "#9ca3af",
}

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
for k, v in {
    "staff_name": "", "staff_id": None, "is_admin": False,
    "view": "bulletin", "viewing_edition_id": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════════════════
# SHARED UI
# ══════════════════════════════════════════════════════════════════════════════
def app_header():
    ab = '<span class="admin-badge">Admin</span>' if st.session_state.is_admin else ""
    st.markdown(
        '<div class="site-header">'
        + '<div style="display:flex;align-items:center;">'
        + '<div class="site-logo">📋</div>'
        + '<div><div class="site-title">CLC Staff Bulletin</div>'
        + '<div class="site-sub">Cowandilla Learning Centre</div></div></div>'
        + '<div style="display:flex;align-items:center;gap:10px;">'
        + ab
        + '<div class="user-chip">👤 ' + st.session_state.staff_name + '</div>'
        + '</div></div>',
        unsafe_allow_html=True
    )
    _, so = st.columns([11, 1])
    with so:
        if st.button("Sign out", key="signout"):
            for k in ["staff_name", "staff_id", "is_admin"]:
                st.session_state[k] = ("" if k == "staff_name" else
                                       None if k == "staff_id" else False)
            st.rerun()

def nav_bar(active):
    tabs = [("bulletin", "📖 This Week")]
    if st.session_state.is_admin:
        tabs += [("compose", "Compose and Send"), ("staff", "👥 Staff")]
    tabs.append(("archive", "🗂 Past Bulletins"))
    cols = st.columns(len(tabs))
    for i, (view, label) in enumerate(tabs):
        with cols[i]:
            if st.button(label, key="nav_" + view,
                         type="primary" if active == view else "secondary",
                         use_container_width=True):
                nav(view)
    st.write("")

def render_bulletin(edition, show_ack=True):
    notices = db_get_notices(edition["id"])
    acked   = has_acked_edition(edition["id"], st.session_state.staff_name)
    n_items = len(notices)

    ack_pill = ""
    if show_ack:
        if acked:
            ack_pill = ('<span style="background:#d1fae5;color:#065f46;border-radius:20px;'
                        'padding:3px 12px;font-size:12px;font-weight:700;">Acknowledged</span>')
        else:
            ack_pill = ('<span style="background:#fef3c7;color:#b45309;border-radius:20px;'
                        'padding:3px 12px;font-size:12px;font-weight:700;">Awaiting acknowledgement</span>')

    st.markdown(
        '<div style="background:linear-gradient(135deg,var(--navy),var(--navy-mid));'
        'border-radius:var(--radius-lg);padding:22px 28px;margin-bottom:24px;">'
        '<div style="font-size:11px;font-weight:700;text-transform:uppercase;'
        'letter-spacing:0.1em;color:rgba(255,255,255,0.5);margin-bottom:6px;">CLC Staff Bulletin</div>'
        '<div style="font-size:26px;font-weight:800;color:white;margin-bottom:8px;">'
        + edition["week_label"]
        + '</div><div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">'
        + '<span style="font-size:13px;color:rgba(255,255,255,0.6);">Sent '
        + fmt_date(edition.get("published_at"))
        + " · " + str(n_items) + (" items" if n_items != 1 else " item")
        + "</span>" + ack_pill + "</div></div>",
        unsafe_allow_html=True
    )

    if not notices:
        st.info("No items in this bulletin.")
        return

    for n in notices:
        cat    = n.get("category", "general")
        label  = CAT_LABELS.get(cat, cat.title())
        badge  = CAT_BADGE.get(cat, CAT_BADGE["general"])
        border = CAT_BORDER.get(cat, CAT_BORDER["general"])
        body   = re.sub('<[^<]+?>', '', n.get("content", ""))

        st.markdown(
            '<div style="background:var(--white);border:1px solid var(--border);'
            'border-radius:var(--radius);padding:18px 22px;margin-bottom:10px;'
            'border-left:4px solid ' + border + ';">'
            '<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
            '<span style="padding:2px 10px;border-radius:20px;font-size:11px;font-weight:700;'
            + badge + '">' + label + '</span>'
            '<span style="font-size:12px;color:var(--ink-faint);">from '
            + n.get("author", "Admin") + '</span></div>'
            '<div style="font-size:16px;font-weight:700;color:var(--ink);margin-bottom:8px;">'
            + n["title"] + '</div>'
            '<div style="font-size:14px;color:var(--ink);line-height:1.7;white-space:pre-wrap;">'
            + body + '</div></div>',
            unsafe_allow_html=True
        )

    if show_ack:
        st.write("")
        if acked:
            st.success("You have acknowledged this bulletin.")
        else:
            if st.button("Mark as Read and Acknowledge", type="primary", use_container_width=True):
                ack_all(edition["id"], st.session_state.staff_name)
                st.success("Acknowledged — thank you!")
                time.sleep(1)
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════════════════════════════
def show_login():
    st.markdown("## 📋 CLC Staff Bulletin")
    st.markdown("**Cowandilla Learning Centre — LBU**")
    st.write("")
    st.markdown("Select your name and enter your PIN to continue.")
    st.write("")

    staff_names = db_get_staff_names()
    if not staff_names:
        st.warning("No staff set up yet. Please contact your administrator.")
        return

    name = st.selectbox("Your name", ["Select your name"] + staff_names)
    pin  = st.text_input("PIN", type="password", placeholder="Enter your PIN")

    if st.button("Sign In", type="primary"):
        if name == "Select your name":
            st.error("Please select your name.")
        elif not pin.strip():
            st.error("Please enter your PIN.")
        else:
            # Try normal PIN verification
            staff = db_verify_pin(name, pin)

            # Fallback: master password from secrets
            master = st.secrets.get("ADMIN_PASSWORD", st.secrets.get("SUPABASE_KEY", "")[:8])
            if not staff and pin.strip() == master:
                # Find the staff record by name only
                all_staff = db_get_staff_list()
                staff = next((s for s in all_staff if s["name"] == name), None)
                if staff:
                    staff["_master_login"] = True

            if staff:
                st.session_state.staff_name = staff["name"]
                st.session_state.staff_id   = staff.get("id")
                st.session_state.is_admin   = staff.get("role") == "admin" or staff.get("_master_login", False)
                st.rerun()
            else:
                st.error("Incorrect PIN. Please try again.")
    st.caption("Forgotten your PIN? Contact your administrator.")


# ══════════════════════════════════════════════════════════════════════════════
# THIS WEEK'S BULLETIN
# ══════════════════════════════════════════════════════════════════════════════
def show_bulletin():
    app_header()
    nav_bar("bulletin")
    published = db_get_current_published()
    if not published:
        st.markdown(
            '<div style="text-align:center;padding:60px 20px;">'
            '<div style="font-size:40px;margin-bottom:16px;">📭</div>'
            '<div style="font-size:18px;font-weight:700;color:var(--ink);margin-bottom:8px;">'
            'No bulletin this week yet</div>'
            '<div style="font-size:14px;color:var(--ink-light);">'
            'The weekly bulletin is usually sent on Wednesday morning.</div></div>',
            unsafe_allow_html=True
        )
        return
    render_bulletin(published, show_ack=True)


# ══════════════════════════════════════════════════════════════════════════════
# COMPOSE AND SEND
# ══════════════════════════════════════════════════════════════════════════════
def show_compose():
    app_header()
    nav_bar("compose")
    if not st.session_state.is_admin:
        st.error("Admin access only.")
        return

    edition = db_get_or_create_edition()
    if not edition:
        st.error("Could not load current edition. Check Supabase connection.")
        return

    notices = db_get_notices(edition["id"])
    is_sent = edition.get("status") == "published"

    if is_sent:
        st.markdown(
            '<div style="background:#d1fae5;border:1px solid #6ee7b7;'
            'border-radius:var(--radius);padding:14px 20px;margin-bottom:20px;">'
            '<div style="font-weight:700;color:#065f46;font-size:15px;">Sent — '
            + edition["week_label"] + '</div>'
            '<div style="font-size:13px;color:#047857;margin-top:2px;">Published '
            + fmt_date(edition.get("published_at")) + " · " + str(len(notices))
            + (" items" if len(notices) != 1 else " item") + "</div></div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div style="background:var(--amber-light);border:2px solid #F59E0B;'
            'border-radius:var(--radius);padding:14px 20px;margin-bottom:20px;">'
            '<div style="font-weight:700;color:var(--amber);font-size:15px;">Draft — '
            + edition["week_label"] + '</div>'
            '<div style="font-size:13px;color:var(--amber);margin-top:2px;">'
            + str(len(notices)) + (" items" if len(notices) != 1 else " item")
            + " · Not sent yet</div></div>",
            unsafe_allow_html=True
        )

    if notices:
        st.markdown("#### Items")
        for n in notices:
            cat    = n.get("category", "general")
            label  = CAT_LABELS.get(cat, cat.title())
            badge  = CAT_BADGE.get(cat, CAT_BADGE["general"])
            body   = re.sub('<[^<]+?>', '', n.get("content", ""))
            preview = body[:120] + ("..." if len(body) > 120 else "")
            c1, c2 = st.columns([11, 1])
            with c1:
                st.markdown(
                    '<div style="background:var(--white);border:1px solid var(--border);'
                    'border-radius:var(--radius);padding:12px 18px;margin-bottom:6px;">'
                    '<span style="padding:2px 9px;border-radius:20px;font-size:11px;font-weight:700;'
                    + badge + '">' + label + '</span>'
                    '<span style="font-size:15px;font-weight:700;color:var(--ink);margin-left:10px;">'
                    + n["title"] + '</span>'
                    '<div style="font-size:13px;color:var(--ink-light);margin-top:5px;">'
                    + preview + '</div></div>',
                    unsafe_allow_html=True
                )
            with c2:
                if not is_sent:
                    st.write("")
                    if st.button("X", key="del_" + str(n["id"]), help="Remove"):
                        db_delete_notice(n["id"])
                        st.rerun()
    elif not is_sent:
        st.info("No items yet — add your first item below.")

    st.write("")

    if not is_sent:
        with st.expander("Add Item", expanded=len(notices) == 0):
            with st.form("add_item", clear_on_submit=True):
                cat     = st.selectbox("Category", list(CAT_LABELS.keys()),
                                       format_func=lambda x: CAT_LABELS[x])
                title   = st.text_input("Subject / Title",
                                        placeholder="e.g. Reminder: Staff PD next Friday")
                content = st.text_area("Body", height=140,
                                       placeholder="Write your message here...")
                if st.form_submit_button("Add to Bulletin", type="primary", use_container_width=True):
                    if not title.strip():
                        st.error("Please enter a title.")
                    elif not content.strip():
                        st.error("Please enter a body.")
                    else:
                        db_create_notice(edition["id"], title.strip(), content.strip(),
                                         cat, st.session_state.staff_name)
                        st.success("Added")
                        time.sleep(0.3)
                        st.rerun()

        if notices:
            st.markdown("---")
            if not st.session_state.get("confirm_send"):
                if st.button("Send to All Staff", type="primary", use_container_width=True):
                    st.session_state["confirm_send"] = True
                    st.rerun()
            else:
                staff_list = db_get_staff_list()
                emails     = [s["email"] for s in staff_list if s.get("email")]
                st.warning("This will email " + str(len(emails)) +
                           " staff and log to meeting minutes. Confirm?")
                s1, s2 = st.columns(2)
                with s1:
                    if st.button("Yes, Send Now", type="primary", use_container_width=True):
                        if db_publish_edition(edition["id"], st.session_state.staff_name):
                            send_edition_notification(
                                edition["week_label"], len(notices), emails,
                                st.secrets.get("APP_URL", "")
                            )
                            st.session_state["confirm_send"] = False
                            st.success("Bulletin sent!")
                            time.sleep(1.5)
                            st.rerun()
                with s2:
                    if st.button("Cancel", use_container_width=True):
                        st.session_state["confirm_send"] = False
                        st.rerun()

    if is_sent:
        st.markdown("---")
        st.markdown("#### Acknowledgements")
        rows    = db_get_ack_summary(edition["id"])
        n_acked = sum(1 for r in rows if r["Acknowledged"] == "Yes")
        st.caption(str(n_acked) + " of " + str(len(rows)) + " staff acknowledged")
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAST BULLETINS
# ══════════════════════════════════════════════════════════════════════════════
def show_archive():
    app_header()
    nav_bar("archive")
    st.markdown('<div class="page-heading">Past <span class="accent">Bulletins</span></div>',
                unsafe_allow_html=True)
    editions = [e for e in db_get_all_editions() if e.get("status") == "published"]
    if not editions:
        st.info("No bulletins sent yet.")
        return
    for ed in editions:
        notices = db_get_notices(ed["id"])
        acked   = has_acked_edition(ed["id"], st.session_state.staff_name)
        c1, c2  = st.columns([5, 1])
        with c1:
            st.markdown(
                '<div style="background:var(--white);border:1px solid var(--border);'
                'border-radius:var(--radius);padding:14px 20px;margin-bottom:4px;">'
                '<div style="font-size:15px;font-weight:700;color:var(--ink);">'
                + ed["week_label"] + '</div>'
                '<div style="font-size:12px;color:var(--ink-faint);margin-top:3px;">Sent '
                + fmt_date(ed.get("published_at")) + " · " + str(len(notices))
                + (" items" if len(notices) != 1 else " item")
                + " · " + ("Acknowledged" if acked else "Pending") + "</div></div>",
                unsafe_allow_html=True
            )
        with c2:
            st.write("")
            if st.button("View", key="arch_" + str(ed["id"]), use_container_width=True):
                nav("archive_week", edition_id=ed["id"])
        st.write("")

def show_archive_week():
    app_header()
    ed = db_get_edition(st.session_state.viewing_edition_id)
    if not ed:
        nav("archive")
        return
    if st.button("Back to Past Bulletins"):
        nav("archive")
    render_bulletin(ed, show_ack=True)


# ══════════════════════════════════════════════════════════════════════════════
# STAFF MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
def show_staff():
    app_header()
    nav_bar("staff")
    if not st.session_state.is_admin:
        st.error("Admin access only.")
        return
    st.markdown('<div class="page-heading">Staff <span class="accent">Management</span></div>',
                unsafe_allow_html=True)
    staff = db_get_staff_list()

    with st.expander("Add New Staff Member", expanded=len(staff) == 0):
        with st.form("add_staff"):
            c1, c2 = st.columns(2)
            with c1:
                nn = st.text_input("Full Name")
                nr = st.selectbox("Role", ["staff", "admin"])
            with c2:
                ne = st.text_input("School Email")
                np = st.text_input("Initial PIN", type="password", help="Min 4 characters")
            if st.form_submit_button("Add Staff Member", type="primary"):
                if not nn.strip():
                    st.error("Name required.")
                elif not ne.strip() or "@" not in ne:
                    st.error("Valid email required.")
                elif len(np.strip()) < 4:
                    st.error("PIN must be at least 4 characters.")
                else:
                    if db_add_staff(nn.strip(), ne.strip(), np.strip(), nr):
                        st.success(nn + " added.")
                        time.sleep(0.8)
                        st.rerun()

    st.write("")
    st.markdown("### Active Staff (" + str(len(staff)) + ")")
    if not staff:
        st.info("No staff added yet.")
        return

    for s in staff:
        c1, c2, c3, c4 = st.columns([3, 3, 1, 1])
        with c1:
            role_note = " (Admin)" if s.get("role") == "admin" else ""
            st.markdown("**" + s["name"] + "**" + role_note)
        with c2:
            st.caption(s.get("email", ""))
        with c3:
            if st.button("Reset PIN", key="reset_" + str(s["id"])):
                st.session_state["resetting_" + str(s["id"])] = True
        with c4:
            if st.button("Remove", key="rm_" + str(s["id"])):
                st.session_state["confirm_remove_" + str(s["id"])] = True

        if st.session_state.get("confirm_remove_" + str(s["id"])):
            st.warning("Remove " + s["name"] + "? Their history is kept.")
            rc1, rc2 = st.columns(2)
            with rc1:
                if st.button("Yes, remove", key="crm_" + str(s["id"]), type="primary"):
                    db_remove_staff(s["id"])
                    st.session_state.pop("confirm_remove_" + str(s["id"]), None)
                    st.rerun()
            with rc2:
                if st.button("Cancel", key="cncrm_" + str(s["id"])):
                    st.session_state.pop("confirm_remove_" + str(s["id"]), None)
                    st.rerun()

        if st.session_state.get("resetting_" + str(s["id"])):
            with st.form("pf_" + str(s["id"])):
                np2 = st.text_input("New PIN for " + s["name"], type="password")
                pf1, pf2 = st.columns(2)
                with pf1:
                    if st.form_submit_button("Set PIN", type="primary"):
                        if len(np2.strip()) < 4:
                            st.error("Min 4 characters.")
                        else:
                            db_set_pin(s["id"], np2.strip())
                            st.success("PIN updated for " + s["name"] + ".")
                            st.session_state.pop("resetting_" + str(s["id"]), None)
                            time.sleep(0.8)
                            st.rerun()
                with pf2:
                    if st.form_submit_button("Cancel"):
                        st.session_state.pop("resetting_" + str(s["id"]), None)
                        st.rerun()
        st.divider()

    st.markdown("---")
    st.markdown("### Change Your Own PIN")
    with st.form("own_pin"):
        op1, op2 = st.columns(2)
        with op1:
            cur_pin = st.text_input("Current PIN", type="password")
        with op2:
            new_pin = st.text_input("New PIN", type="password")
        if st.form_submit_button("Update My PIN"):
            if not db_verify_pin(st.session_state.staff_name, cur_pin):
                st.error("Current PIN is incorrect.")
            elif len(new_pin.strip()) < 4:
                st.error("New PIN must be at least 4 characters.")
            else:
                if db_set_pin(st.session_state.staff_id, new_pin.strip()):
                    st.success("PIN updated.")


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
