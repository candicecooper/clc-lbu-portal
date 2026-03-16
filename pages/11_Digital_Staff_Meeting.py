from theme import apply_clc_theme
import streamlit as st
import re
import time
import pandas as pd
from datetime import datetime, date, timedelta, timezone

from database import (
    get_or_create_current_edition, get_edition, get_notices_for_edition,
    get_current_published_edition, get_all_editions,
    publish_edition, unpublish_edition, seed_term_weeks, sync_to_staff_minutes, create_notice, get_notice,
    get_actions, get_poll_options, get_poll_votes, get_attachments,
    get_attachment_bytes,
    record_read, record_acknowledgement, record_poll_vote, record_comment,
    get_responses, get_comments, has_acknowledged, has_voted,
    get_staff_list, get_staff_names, add_staff_member, remove_staff_member,
    set_staff_pin, verify_pin, is_admin,
    get_edition_ack_summary,
    get_agenda_items, save_agenda_item, delete_agenda_item,
    get_agenda_acks, record_agenda_ack, has_agenda_acked,
    get_agenda_comments, save_agenda_comment,
    get_agenda_poll_options, get_agenda_poll_votes,
    save_agenda_poll_option, record_agenda_vote, has_agenda_voted,
    get_global_timetable, save_global_timetable, get_global_timetable_bytes,
    save_agenda_attachment, get_agenda_attachments,
    get_agenda_attachment_bytes, delete_agenda_attachment
)
try:
    from email_utils import send_edition_notification
except ImportError:
    def send_edition_notification(*args, **kwargs):
        return False

# ── Supabase client for timetable storage ─────────────────────────────────────
@st.cache_resource
def _get_supabase():
    from supabase import create_client
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def upload_timetable(edition_id: str, file_bytes: bytes, filename: str) -> tuple[bool, str]:
    """Upload a timetable PDF to Supabase storage. Returns (success, storage_path)."""
    try:
        sb = _get_supabase()
        path = f"timetables/{edition_id}/{filename}"
        sb.storage.from_("notice-attachments").upload(
            path, file_bytes,
            file_options={"content-type": "application/pdf", "upsert": "true"}
        )
        return True, path
    except Exception as e:
        return False, str(e)

def get_timetable_bytes(storage_path: str) -> bytes | None:
    """Retrieve timetable PDF bytes from Supabase storage."""
    try:
        sb = _get_supabase()
        return sb.storage.from_("notice-attachments").download(storage_path)
    except:
        return None

def get_timetable_path(edition_id: str) -> str | None:
    """Get the stored timetable path from agenda items for this edition."""
    try:
        sb = _get_supabase()
        res = sb.table("agenda_items").select("content").eq("edition_id", edition_id).eq("section", "timetable").order("created_at", desc=True).limit(1).execute()
        if res.data:
            content = res.data[0]["content"]
            # content stores "TIMETABLE_PATH::<path>::<filename>"
            if content.startswith("TIMETABLE_PATH::"):
                parts = content.split("::")
                return parts[1] if len(parts) > 1 else None
        return None
    except:
        return None

def get_timetable_filename(edition_id: str) -> str | None:
    """Get the stored timetable filename from agenda items."""
    try:
        sb = _get_supabase()
        res = sb.table("agenda_items").select("content").eq("edition_id", edition_id).eq("section", "timetable").order("created_at", desc=True).limit(1).execute()
        if res.data:
            content = res.data[0]["content"]
            if content.startswith("TIMETABLE_PATH::"):
                parts = content.split("::")
                return parts[2] if len(parts) > 2 else "timetable.pdf"
        return None
    except:
        return None

st.set_page_config(page_title="CLC Digital Staff Meeting", page_icon="📋",
                   layout="wide", initial_sidebar_state="collapsed")
apply_clc_theme()

# ── Back to Portal ─────────────────────────────────────────────────────────────
if st.sidebar.button("🏠 Back to Staff Portal", use_container_width=True, key="back_to_portal"):
    st.markdown(f'<meta http-equiv="refresh" content="0;url=https://16cefb77.clc-portal.pages.dev/">', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# DESIGN — Portal-aligned navy theme
# ══════════════════════════════════════════════════════════════════════════════

# ── Session state ──────────────────────────────────────────────────────────────
for k,v in {
    "staff_name":"", "staff_id":None, "is_admin":False, "login_attempts":0,
    "view":"meeting", "current_notice_id":None, "viewing_edition_id":None,
    "flow_step":0, "poll_voted":False, "cat_filter":"All",
    "agenda_view":None, "meeting_expanded":False, "draft_agenda_view":None,
}.items():
    if k not in st.session_state: st.session_state[k]=v

CAT_LABELS = {"general":"General","policy":"Policy Update","action":"Action Required","reminder":"Reminder","update":"Update"}
FILE_ICONS = {"pdf":"📄","doc":"📝","docx":"📝","xls":"📊","xlsx":"📊","ppt":"📑","pptx":"📑","jpg":"🖼","jpeg":"🖼","png":"🖼","mp4":"🎬","mp3":"🎵","zip":"🗜","txt":"📃"}
AGENDA_SECTIONS = [
    ("whs",           "⚠️ WHS",           "Work Health & Safety"),
    ("finance",       "💰 Finance",         "Financial updates"),
    ("special_events","🎉 Special Events",  "Upcoming events"),
    ("social_club",   "☕ Social Club",     "Social club news"),
    ("pac",           "👥 PAC",             "Parent Advisory Committee"),
    ("timetable",     "📅 Timetable",       "Current timetable"),
]

def file_icon(n):
    ext = n.rsplit(".",1)[-1].lower() if "." in n else ""
    return FILE_ICONS.get(ext,"📎")

def fmt_bytes(b):
    if not b: return ""
    b=int(b)
    if b<1024: return f"{b} B"
    if b<1024**2: return f"{b/1024:.1f} KB"
    return f"{b/1024**2:.1f} MB"

def fmt_date(d):
    if not d: return ""
    try: return datetime.fromisoformat(str(d).replace("Z","+00:00")).strftime("%-d %b %Y")
    except: return str(d)[:10]

def nav(view, notice_id=None, edition_id=None):
    st.session_state.view=view
    if notice_id  is not None: st.session_state.current_notice_id=notice_id; st.session_state.flow_step=0; st.session_state.poll_voted=False
    if edition_id is not None: st.session_state.viewing_edition_id=edition_id
    st.rerun()

def is_wednesday_or_later(ed):
    if not ed or ed.get("status")!="published": return False
    try: return date.today()>=date.fromisoformat(str(ed["week_start"]))+timedelta(days=2)
    except: return False

# ── Deadline helpers (Adelaide time: ACDT UTC+10:30) ──────────────────────────
_ADELAIDE = timezone(timedelta(hours=10, minutes=30))

def adelaide_today() -> date:
    """Current date in Adelaide time."""
    return datetime.now(tz=_ADELAIDE).date()

def get_edition_monday(edition) -> date | None:
    if not edition: return None
    try: return date.fromisoformat(str(edition["week_start"]))
    except: return None

def is_submission_locked(edition) -> bool:
    """True for staff when today (Adelaide) is past Monday COB."""
    monday = get_edition_monday(edition)
    if not monday: return False
    return adelaide_today() > monday

def is_tuesday_review_day(edition) -> bool:
    """True on Tuesday when the edition is still a draft — admin should review."""
    monday = get_edition_monday(edition)
    if not monday or not edition: return False
    if edition.get("status") == "published": return False
    return adelaide_today() == monday + timedelta(days=1)

def thursday_deadline(edition) -> date | None:
    monday = get_edition_monday(edition)
    if not monday: return None
    return monday + timedelta(days=3)

def days_until(d: date) -> int:
    return (d - adelaide_today()).days

# ══════════════════════════════════════════════════════════════════════════════
# HEADER & NAV
# ══════════════════════════════════════════════════════════════════════════════
def app_header():
    ab = '<span class="admin-badge">Admin</span>' if st.session_state.is_admin else ""
    st.markdown(f"""
    <div class="site-header">
      <div style="display:flex;align-items:center;">
        <div class="site-logo">📋</div>
        <div>
          <div class="site-title">CLC Digital Staff Meeting</div>
          <div class="site-sub">Cowandilla Learning Centre</div>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:10px;">
        {ab}<div class="user-chip">👤 {st.session_state.staff_name}</div>
      </div>
    </div>""", unsafe_allow_html=True)
    _, so = st.columns([11,1])
    with so:
        if st.button("Sign out", key="signout"):
            for k in ["staff_name","staff_id","is_admin","login_attempts"]:
                st.session_state[k] = "" if k=="staff_name" else (None if k=="staff_id" else False if k=="is_admin" else 0)
            st.rerun()

def nav_bar(active):
    draft     = get_or_create_current_edition()
    published = get_current_published_edition()
    locked    = is_submission_locked(draft) and not st.session_state.is_admin

    # Build week labels for tabs
    pub_label   = published["week_label"] if published else "No meeting yet"
    draft_label = draft["week_label"] if draft else "Upcoming"

    if locked:
        submit_label = f"🔒 {draft_label} — Closed"
    else:
        submit_label = f"✏️ {draft_label} — Submit Items"

    meeting_label = f"📖 {pub_label}" if published else "📖 This Week's Meeting"

    tabs = [("meeting", meeting_label), ("submit", submit_label), ("archive", "🗂 Archive")]
    if st.session_state.is_admin:
        tabs.append(("staff", "👥 Staff"))

    cols = st.columns(len(tabs))
    for i, (view, label) in enumerate(tabs):
        with cols[i]:
            if st.button(label, key=f"nav_{view}",
                         type="primary" if active == view else "secondary",
                         use_container_width=True):
                nav(view)

    # Context strip — shows what each tab means at a glance
    today = adelaide_today()
    day_name = today.strftime("%A")
    if published and draft and published["id"] != draft["id"]:
        # Different weeks — most common state
        st.markdown(f"""
        <div style="display:flex;gap:8px;margin-top:6px;margin-bottom:4px;flex-wrap:wrap;">
          <div style="background:#d1fae5;border-radius:8px;padding:4px 12px;font-size:12px;color:#065f46;font-weight:600;">
            📖 Reading: {pub_label}
          </div>
          <div style="background:#fef3c7;border-radius:8px;padding:4px 12px;font-size:12px;color:#92400e;font-weight:600;">
            ✏️ Submitting for: {draft_label}
          </div>
          <div style="background:var(--navy-light);border-radius:8px;padding:4px 12px;font-size:12px;color:var(--navy);font-weight:600;">
            📅 Today: {day_name}
          </div>
        </div>""", unsafe_allow_html=True)
    elif published:
        st.markdown(f"""
        <div style="display:flex;gap:8px;margin-top:6px;margin-bottom:4px;flex-wrap:wrap;">
          <div style="background:#d1fae5;border-radius:8px;padding:4px 12px;font-size:12px;color:#065f46;font-weight:600;">
            📖 Current meeting: {pub_label}
          </div>
          <div style="background:var(--navy-light);border-radius:8px;padding:4px 12px;font-size:12px;color:var(--navy);font-weight:600;">
            📅 Today: {day_name}
          </div>
        </div>""", unsafe_allow_html=True)
    st.write("")

# ══════════════════════════════════════════════════════════════════════════════
# LOGIN  — compact layout, no scroll required
# ══════════════════════════════════════════════════════════════════════════════
def show_login():
    left, right = st.columns([1.2, 1])

    # ── Left: branding panel ──────────────────────────────────────────────────
    with left:
        st.markdown("""
        <div class="login-panel-left">
          <div class="login-brand-icon">📋</div>
          <div class="login-brand-title">CLC Digital<br>Staff Meeting</div>
          <div class="login-brand-sub">Cowandilla Learning Centre — LBU</div>
          <div class="login-info-pills">
            <div class="login-info-pill">
              <div class="lip-icon">📅</div>
              <div class="lip-text"><strong>Submit items</strong> by Monday COB each week</div>
            </div>
            <div class="login-info-pill">
              <div class="lip-icon">📖</div>
              <div class="lip-text"><strong>Meeting goes live</strong> Wednesday morning</div>
            </div>
            <div class="login-info-pill">
              <div class="lip-icon">✅</div>
              <div class="lip-text"><strong>Acknowledge all items</strong> by Thursday COB</div>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

    # ── Right: login form ─────────────────────────────────────────────────────
    with right:
        st.markdown("""
        <div class="login-panel-right">
          <div class="login-form-title">Welcome back</div>
          <div class="login-form-sub">Select your name and enter your PIN to access this week's meeting.</div>
        </div>""", unsafe_allow_html=True)

        staff_names = get_staff_names()
        if not staff_names:
            st.warning("No staff set up yet. Please contact your administrator.")
            return

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        name = st.selectbox("Your name", ["— Select your name —"] + staff_names,
                            label_visibility="visible")
        pin  = st.text_input("PIN", type="password", placeholder="Enter your PIN")

        if st.session_state.login_attempts >= 5:
            st.error("Too many failed attempts. Contact your administrator to reset your PIN.")
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
# THIS WEEK'S MEETING
# ══════════════════════════════════════════════════════════════════════════════
def show_meeting():
    app_header()
    nav_bar("meeting")

    published = get_current_published_edition()

    # ── No published meeting yet ─────────────────────────────────────────────
    if not published:
        st.markdown('<div class="page-heading">This Week\'s <span class="accent">Meeting</span></div>', unsafe_allow_html=True)
        if st.session_state.is_admin:
            _show_draft_panel()
        else:
            st.markdown("""
            <div style="background:var(--white);border:1px solid var(--border);border-radius:var(--radius-lg);padding:36px;text-align:center;margin-top:20px;">
              <div style="font-size:40px;margin-bottom:14px;">📅</div>
              <div style="font-size:18px;font-weight:700;color:var(--ink);margin-bottom:8px;">Not published yet</div>
              <div style="font-size:14px;color:var(--ink-light);">This week's meeting will be available from Wednesday morning.<br>
              To submit an agenda item, use the <b>Submit for Next Week</b> tab — deadline is <b>Monday COB</b>.</div>
            </div>""", unsafe_allow_html=True)
        return

    # ── Acknowledgement deadline banner ──────────────────────────────────────
    if not st.session_state.is_admin:
        thu = thursday_deadline(published)
        if thu:
            days = days_until(thu)
            if days > 0:
                st.markdown(f'<div class="deadline-banner">📅 Please read and acknowledge all items by <strong>Thursday {thu.strftime("%-d %b")} (COB)</strong> — {days} day{"s" if days!=1 else ""} to go.</div>', unsafe_allow_html=True)
            elif days == 0:
                st.markdown(f'<div class="deadline-banner">⏰ Today is the acknowledgement deadline — <strong>Thursday COB</strong>. Please complete your acknowledgements now.</div>', unsafe_allow_html=True)
            elif days < 0:
                st.markdown(f'<div class="deadline-overdue">⚠️ The acknowledgement deadline was <strong>Thursday {thu.strftime("%-d %b")}</strong>. Please acknowledge any outstanding items immediately.</div>', unsafe_allow_html=True)

    # ── Meeting header ────────────────────────────────────────────────────────
    notices   = get_notices_for_edition(published["id"])
    n_notices = len(notices)
    n_unacked = sum(1 for n in notices if not has_acknowledged(n["id"], st.session_state.staff_name))
    ack_badge = (
        f'<span style="background:#fef3c7;color:#b45309;border-radius:20px;padding:4px 12px;font-size:12px;font-weight:700;">{n_unacked} item{"s" if n_unacked!=1 else ""} need{"s" if n_unacked==1 else ""} acknowledgement</span>'
        if n_unacked > 0 else
        '<span style="background:#d1fae5;color:#065f46;border-radius:20px;padding:4px 12px;font-size:12px;font-weight:700;">✓ All acknowledged</span>'
    )
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,var(--navy),var(--navy-mid));border-radius:var(--radius-lg);padding:24px 28px;margin-bottom:20px;">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:rgba(255,255,255,0.55);margin-bottom:6px;">📖 This Week's Staff Meeting</div>
      <div style="font-size:26px;font-weight:800;color:white;margin-bottom:8px;">{published["week_label"]}</div>
      <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
        <span style="font-size:13px;color:rgba(255,255,255,0.65);">Published {fmt_date(published.get("published_at"))} · {n_notices} notice{"s" if n_notices!=1 else ""}</span>
        {ack_badge}
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Standing agenda items ─────────────────────────────────────────────────
    st.markdown('<div class="section-label">📌 Standing Agenda Items</div>', unsafe_allow_html=True)
    if st.session_state.get("agenda_view"):
        _show_agenda_detail(published["id"], st.session_state.agenda_view)
    else:
        _show_agenda_grid(published["id"])

    # ── General notices ───────────────────────────────────────────────────────
    notices = get_notices_for_edition(published["id"])
    if notices:
        st.markdown('<div class="section-label">📋 Notices & Updates</div>', unsafe_allow_html=True)
        cats = ["All","Needs My Action"]+list(CAT_LABELS.values())
        fcols = st.columns(len(cats))
        for i,cat in enumerate(cats):
            with fcols[i]:
                if st.button(cat, key=f"cf_{cat}", type="primary" if st.session_state.cat_filter==cat else "secondary", use_container_width=True):
                    st.session_state.cat_filter=cat; st.rerun()
        st.write("")

        for n in notices:
            cat = n.get("category","general")
            cat_label = CAT_LABELS.get(cat,cat.title())
            ackd = has_acknowledged(n["id"], st.session_state.staff_name)
            if st.session_state.cat_filter not in ("All", cat_label):
                if not (st.session_state.cat_filter=="Needs My Action" and not ackd): continue

            preview = re.sub('<[^<]+?>','', n.get("content",""))[:140]+"…"
            flags = []
            if n.get("has_actions"): flags.append("📋 Actions")
            if n.get("has_poll"):    flags.append("📊 Poll")
            if n.get("has_comments"): flags.append("💬 Feedback")
            atts = get_attachments(n["id"])
            if atts: flags.append(f"📎 {len(atts)}")
            flags_html = "  ".join(f'<span style="font-size:11px;color:var(--ink-faint)">{f}</span>' for f in flags)

            st.markdown(f"""
            <div class="card {cat}">
              <div class="card-meta">
                <span class="badge badge-{cat}">{cat_label}</span>
                <span class="badge {'badge-done' if ackd else 'badge-pending'}">{'✓ Acknowledged' if ackd else '⚠ Needs acknowledgement'}</span>
                <span>by {n.get('author','')} {('· '+n.get('audience','')) if n.get('audience')!='All Staff' else ''}</span>
              </div>
              <div class="card-title">{n['title']}</div>
              <div class="card-preview">{preview}</div>
              <div style="margin-top:8px">{flags_html}</div>
            </div>""", unsafe_allow_html=True)

            bc1,bc2,bc3 = st.columns([2,1,1])
            with bc1:
                lbl = "✓ Read Again" if ackd else "Read & Acknowledge →"
                if st.button(lbl, key=f"read_{n['id']}", type="primary" if not ackd else "secondary"):
                    record_read(n["id"], st.session_state.staff_name)
                    nav("read", notice_id=n["id"])
            with bc2:
                if st.button("Responses", key=f"resp_{n['id']}"): nav("responses", notice_id=n["id"])
            st.write("")

    if st.session_state.is_admin:
        _show_draft_panel()

# ══════════════════════════════════════════════════════════════════════════════
# ADMIN DRAFT PANEL
# ══════════════════════════════════════════════════════════════════════════════
def _show_draft_panel():
    draft = get_or_create_current_edition()
    if not draft: return
    draft_notices = get_notices_for_edition(draft["id"])
    monday = get_edition_monday(draft)

    # ── Tuesday review alert ─────────────────────────────────────────────────
    if monday and is_tuesday_review_day(draft):
        st.markdown(f"""
        <div class="admin-review-alert">
          <div class="ara-icon">🔔</div>
          <div>
            <h3>Agenda ready for your review</h3>
            <p>Staff submissions for <strong>{draft['week_label']}</strong> closed yesterday (Monday COB).
            You have {len(draft_notices)} item{"s" if len(draft_notices)!=1 else ""} in the draft.
            Review each item below, then publish when ready.</p>
          </div>
        </div>""", unsafe_allow_html=True)

    # ── Always-expanded draft review ─────────────────────────────────────────
    st.markdown(f"""
    <div style="background:var(--white);border:2px solid var(--navy-border);border-radius:var(--radius-lg);padding:20px 24px;margin-bottom:16px;">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:var(--navy-mid);margin-bottom:4px;">🛠 Admin — Draft Review</div>
      <div style="font-size:18px;font-weight:700;color:var(--ink);">{draft['week_label']}</div>
      <div style="font-size:13px;color:var(--ink-light);margin-top:2px;">{len(draft_notices)} general notice{"s" if len(draft_notices)!=1 else ""} submitted</div>
    </div>""", unsafe_allow_html=True)

    if draft_notices:
        for n in draft_notices:
            cat = n.get("category","general")
            cat_label = CAT_LABELS.get(cat, cat.title())
            content_preview = re.sub('<[^<]+?>','', n.get("content",""))
            # Full content expandable per item
            with st.expander(f"{'📋' if cat=='action' else '📌' if cat=='policy' else '🔔' if cat=='reminder' else '🔵'}  {n['title']}  ·  {cat_label}  ·  by {n.get('author','')}"):
                st.markdown(f'<span class="badge badge-{cat}">{cat_label}</span>', unsafe_allow_html=True)
                st.markdown(f"**Audience:** {n.get('audience','All Staff')}")
                st.markdown("---")
                st.markdown(f'<div class="content-text">{n.get("content","")}</div>', unsafe_allow_html=True)
                actions = get_actions(n["id"])
                if actions:
                    st.markdown("**Action Items:**")
                    for a in actions:
                        st.markdown(f"- {a['action_text']}")
                poll_opts = get_poll_options(n["id"])
                if poll_opts:
                    st.markdown(f"**Poll:** {n.get('poll_question','')}")
                    for o in poll_opts:
                        st.markdown(f"- {o['option_text']}")
    else:
        st.info("No general notices submitted yet for this week.")

    st.write("")

    # ── Publish button ────────────────────────────────────────────────────────
    if not st.session_state.get("confirm_publish"):
        if st.button("🚀 Publish This Week's Meeting", type="primary", use_container_width=True):
            st.session_state["confirm_publish"] = True; st.rerun()
    else:
        st.warning("⚠️ This will email all staff. Are you sure?")
        pc1, pc2 = st.columns(2)
        with pc1:
            if st.button("✓ Yes, Publish Now", type="primary", use_container_width=True):
                ok = publish_edition(draft["id"], st.session_state.staff_name)
                if ok:
                    sync_ok, sync_msg = sync_to_staff_minutes(draft["id"])
                    staff_list = get_staff_list()
                    emails = [s["email"] for s in staff_list if s.get("email")]
                    ok2, msg = send_edition_notification(draft["week_label"], len(draft_notices), emails, st.secrets.get("APP_URL",""))
                    st.session_state["confirm_publish"] = False
                    st.success(f"✅ Published! {'Minutes synced to Team Meetings. ' if sync_ok else ''}{msg if ok2 else ''}")
                    time.sleep(1.5); st.rerun()
        with pc2:
            if st.button("Cancel", use_container_width=True):
                st.session_state["confirm_publish"] = False; st.rerun()

    # ── Manual sync for already-published editions ────────────────────────────
    st.markdown("---")
    st.markdown("**🔁 Sync to Staff Meeting Minutes**")
    st.caption("Manually push a published digital meeting into the Staff Meetings section of the Team Meetings app. Use this for editions published before auto-sync was added.")
    published_eds = [e for e in get_all_editions() if e.get("status") == "published"]
    if published_eds:
        sync_opts = {e["week_label"]: e["id"] for e in published_eds}
        sync_label = st.selectbox("Edition to sync", list(sync_opts.keys()), key="sync_select")
        if st.button("🔁 Sync Now", key="manual_sync_btn"):
            with st.spinner("Syncing…"):
                ok, msg = sync_to_staff_minutes(sync_opts[sync_label])
            if ok:
                st.success(f"✅ {msg}")
            else:
                st.error(f"❌ {msg}")
    else:
        st.info("No published editions to sync.")

    # ── Reopen a published edition ────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**🔓 Reopen a Published Edition**")
    st.caption("Use this to correct a mistake in a published meeting. It will revert it to draft so you can amend and republish.")
    all_eds = get_all_editions()
    published_eds = [e for e in all_eds if e.get("status") == "published"]
    if published_eds:
        ed_options = {e["week_label"]: e["id"] for e in published_eds}
        chosen_label = st.selectbox("Select published edition to reopen", list(ed_options.keys()), key="reopen_select")
        if st.button("🔓 Reopen for Editing", key="reopen_btn"):
            st.session_state["confirm_reopen"] = ed_options[chosen_label]
            st.rerun()
        if st.session_state.get("confirm_reopen") == ed_options.get(chosen_label):
            st.warning(f"⚠️ This will unpublish **{chosen_label}** and return it to draft. Staff will no longer see it as the current meeting. Continue?")
            rc1, rc2 = st.columns(2)
            with rc1:
                if st.button("✓ Yes, Reopen It", type="primary", key="confirm_reopen_yes"):
                    if unpublish_edition(ed_options[chosen_label]):
                        st.session_state.pop("confirm_reopen", None)
                        st.success(f"✅ {chosen_label} is now back in draft. Make your changes, then republish.")
                        time.sleep(1.5); st.rerun()
            with rc2:
                if st.button("Cancel", key="confirm_reopen_no"):
                    st.session_state.pop("confirm_reopen", None); st.rerun()
    else:
        st.info("No published editions to reopen.")


# ══════════════════════════════════════════════════════════════════════════════
# AGENDA GRID & DETAIL
# ══════════════════════════════════════════════════════════════════════════════
def _show_agenda_grid(edition_id):
    items = get_agenda_items(edition_id)
    by_sec = {}
    for it in items:
        by_sec.setdefault(it["section"],[]).append(it)

    cols = st.columns(6)
    for i,(key,label,_) in enumerate(AGENDA_SECTIONS):
        sec_items = by_sec.get(key,[])
        has = len(sec_items)>0
        acked = has_agenda_acked(edition_id, key, st.session_state.staff_name)
        poll_opts = get_agenda_poll_options(edition_id, key)
        comments  = get_agenda_comments(edition_id, key)

        with cols[i]:
            content_html = ""
            if has:
                for it in sec_items[:2]:
                    content_html += f'<div class="agenda-entry"><div class="agenda-entry-author">{it["author"]}</div>{it["content"][:80]}{"…" if len(it["content"])>80 else ""}</div>'
                if len(sec_items)>2:
                    content_html += f'<div style="font-size:11px;color:var(--navy-mid);font-weight:600">+{len(sec_items)-2} more</div>'
            elif poll_opts or comments:
                total_v = sum(get_agenda_poll_votes(edition_id, key).values())
                content_html = f'<div class="agenda-empty">{"📊 "+str(total_v)+" vote(s)" if poll_opts else ""} {"💬 "+str(len(comments))+" comment(s)" if comments else ""}</div>'
            else:
                content_html = '<div class="agenda-empty">Nothing to report.</div>'

            features = []
            if poll_opts: features.append(f"📊 {sum(get_agenda_poll_votes(edition_id,key).values())} votes")
            if comments:  features.append(f"💬 {len(comments)}")
            if acked:     features.append("✓ Acknowledged")
            feat_html = "".join(f'<span class="agenda-feat active">{f}</span>' for f in features) if features else ""

            st.markdown(f"""
            <div class="agenda-card {'has-content' if has else ''}">
              <div class="agenda-section-label {'has-content' if has else ''}">{label}</div>
              {content_html}
              <div class="agenda-features">{feat_html}</div>
            </div>""", unsafe_allow_html=True)

            btn_label = "Open →" if (has or poll_opts or comments) else "Add entry →"
            if st.button(btn_label, key=f"agenda_open_{key}_{edition_id}", use_container_width=True):
                st.session_state.agenda_view = (edition_id, key); st.rerun()


def _show_agenda_detail(edition_id, agenda_key_tuple):
    edition_id, key = agenda_key_tuple
    label = next((l for k,l,_ in AGENDA_SECTIONS if k==key), key)

    if st.button("← Back to Meeting"):
        st.session_state.agenda_view = None; st.rerun()

    items      = get_agenda_items(edition_id)
    # For timetable, filter out the TIMETABLE_PATH storage items from display
    sec_items  = [it for it in items if it["section"]==key and not it["content"].startswith("TIMETABLE_PATH::")]
    poll_opts  = get_agenda_poll_options(edition_id, key)
    poll_votes = get_agenda_poll_votes(edition_id, key)
    comments   = get_agenda_comments(edition_id, key)
    acked      = has_agenda_acked(edition_id, key, st.session_state.staff_name)

    st.markdown(f"""
    <div class="flow-top">
      <div class="flow-title">{label}</div>
      <div class="flow-meta">Standing Agenda Item · {fmt_date(datetime.now().isoformat())}</div>
    </div>
    <div class="flow-body">""", unsafe_allow_html=True)

    # ── TIMETABLE — special PDF section ──────────────────────────────────────
    if key == "timetable":
        timetable_record   = get_global_timetable()
        timetable_filename = timetable_record.get("meta", "timetable.pdf") if timetable_record else None
        pdf_bytes          = get_global_timetable_bytes()

        if pdf_bytes:
            import base64
            b64 = base64.b64encode(pdf_bytes).decode()
            updated = timetable_record.get("updated_at","") if timetable_record else ""
            updated_fmt = fmt_date(updated) if updated else ""
            st.markdown(f"""
            <div style="border:1px solid var(--navy-border);border-radius:var(--radius);overflow:hidden;margin-bottom:12px;">
              <div style="background:var(--navy-light);padding:10px 16px;display:flex;align-items:center;justify-content:space-between;">
                <div style="font-size:13px;font-weight:600;color:var(--navy);">📄 {timetable_filename}</div>
                {f'<div style="font-size:11px;color:var(--ink-light);">Updated {updated_fmt}</div>' if updated_fmt else ''}
              </div>
              <iframe src="data:application/pdf;base64,{b64}" width="100%" height="700px" style="border:none;display:block;"></iframe>
            </div>""", unsafe_allow_html=True)
            st.download_button(
                label=f"⬇ Download {timetable_filename}",
                data=pdf_bytes,
                file_name=timetable_filename,
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.info("No timetable uploaded yet. Admin can upload the current timetable from the Staff tab.")

        st.markdown('</div>', unsafe_allow_html=True)
        st.write("")

        # Acknowledgement
        st.markdown('<div class="section-label">✅ Acknowledgement</div>', unsafe_allow_html=True)
        if acked:
            st.success("✅ You have acknowledged this agenda item.")
        else:
            st.markdown('<div class="ack-box"><h3>Acknowledge Timetable</h3><p>Confirm you have seen the current timetable.</p></div>', unsafe_allow_html=True)
            st.write("")
            if st.checkbox("I have viewed the current timetable"):
                if st.button("✓ Acknowledge", type="primary"):
                    record_agenda_ack(edition_id, key, st.session_state.staff_name)
                    st.success("Acknowledged ✓"); time.sleep(1); st.rerun()
        return

    # ── All other standing sections ───────────────────────────────────────────
    if sec_items:
        for it in sec_items:
            cols_item = st.columns([8, 1]) if st.session_state.is_admin else [None]
            with cols_item[0] if st.session_state.is_admin else st.container():
                st.markdown(f'<div class="agenda-entry"><div class="agenda-entry-author">📝 {it["author"]} · {fmt_date(it["created_at"])}</div>{it["content"]}</div>', unsafe_allow_html=True)
            if st.session_state.is_admin:
                with cols_item[1]:
                    if st.button("🗑", key=f"del_item_{it['id']}", help="Delete this entry"):
                        st.session_state[f"confirm_del_{it['id']}"] = True; st.rerun()
                if st.session_state.get(f"confirm_del_{it['id']}"):
                    st.warning(f"Delete this entry by {it['author']}?")
                    dc1, dc2 = st.columns(2)
                    with dc1:
                        if st.button("Delete", key=f"do_del_{it['id']}", type="primary"):
                            delete_agenda_item(it["id"])
                            st.session_state.pop(f"confirm_del_{it['id']}", None)
                            st.rerun()
                    with dc2:
                        if st.button("Cancel", key=f"cancel_del_{it['id']}"):
                            st.session_state.pop(f"confirm_del_{it['id']}", None); st.rerun()
            st.markdown('<hr>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="agenda-empty" style="font-size:15px;padding:12px 0">Nothing to report this week.</div>', unsafe_allow_html=True)

    with st.expander("+ Add an update to this section", expanded=len(sec_items)==0):
        with st.form(f"agenda_update_{key}"):
            txt = st.text_area("Your update", height=100,
                               placeholder="Type your update here…",
                               label_visibility="collapsed")
            if st.form_submit_button("Save Update", type="primary"):
                if txt.strip():
                    save_agenda_item(edition_id, key, st.session_state.staff_name, txt.strip())
                    st.success("Saved ✓"); time.sleep(0.5); st.rerun()
                else:
                    st.error("Please enter some text.")

    # ── File attachments for this section ─────────────────────────────────────
    agenda_atts = get_agenda_attachments(edition_id, key)
    st.markdown('<div class="section-label">📎 Documents</div>', unsafe_allow_html=True)
    if agenda_atts:
        for att in agenda_atts:
            size_kb = round(att.get("file_size", 0) / 1024, 1)
            ac1, ac2, ac3 = st.columns([5, 1, 1])
            with ac1:
                st.markdown(f'<div class="attach-item"><span style="font-size:18px">📄</span><div><div class="attach-name">{att["filename"]}</div><div class="attach-size">{size_kb} KB · uploaded by {att.get("uploaded_by","")}</div></div></div>', unsafe_allow_html=True)
            with ac2:
                fname, mime, fbytes = get_agenda_attachment_bytes(att["id"])
                if fbytes:
                    st.download_button("⬇", data=fbytes, file_name=fname, mime=mime or "application/octet-stream", key=f"dl_agatt_{att['id']}", use_container_width=True)
            with ac3:
                if st.session_state.is_admin:
                    if st.button("🗑", key=f"del_agatt_{att['id']}", help="Delete"):
                        delete_agenda_attachment(att["id"]); st.rerun()
    else:
        st.caption("No documents attached yet.")

    with st.expander("📤 Upload a document for this section"):
        up_file = st.file_uploader("Choose file", key=f"agatt_upload_{key}", label_visibility="collapsed")
        if up_file:
            if st.button("✓ Attach Document", key=f"agatt_save_{key}", type="primary"):
                up_file.seek(0)
                if save_agenda_attachment(edition_id, key, up_file.name, up_file.read(),
                                          up_file.type or "application/octet-stream",
                                          st.session_state.staff_name):
                    st.success(f"✅ {up_file.name} attached."); time.sleep(0.5); st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    st.write("")

    # Poll
    if poll_opts or st.session_state.is_admin:
        st.markdown('<div class="section-label">📊 Poll</div>', unsafe_allow_html=True)
        if st.session_state.is_admin and not poll_opts:
            with st.expander("+ Add a poll to this section"):
                with st.form(f"agenda_poll_setup_{key}"):
                    pq = st.text_input("Poll question", placeholder="e.g. Are you available for the excursion?")
                    n_opts = st.number_input("Number of options", 2, 6, 2)
                    opts = [st.text_input(f"Option {j+1}", key=f"apo_{key}_{j}") for j in range(int(n_opts))]
                    if st.form_submit_button("Create Poll", type="primary"):
                        valid = [o for o in opts if o.strip()]
                        if len(valid) >= 2:
                            save_agenda_poll_option(edition_id, key, pq, valid)
                            st.success("Poll created ✓"); time.sleep(0.5); st.rerun()
                        else:
                            st.error("Need at least 2 options.")
        if poll_opts:
            question = poll_opts[0].get("question", "") if poll_opts else ""
            if question: st.markdown(f"**{question}**")
            already  = has_agenda_voted(edition_id, key, st.session_state.staff_name)
            total_v  = sum(poll_votes.values()) or 1
            if already:
                for opt in poll_opts:
                    v = poll_votes.get(opt["id"], 0); pct = round(v/total_v*100)
                    st.markdown(f'<div class="poll-label"><span>{opt["option_text"]}</span><span>{v} ({pct}%)</span></div><div class="poll-bar-bg"><div class="poll-bar-fill" style="width:{pct}%"></div></div>', unsafe_allow_html=True)
                st.caption(f"Total votes: {sum(poll_votes.values())}")
            else:
                sel = st.radio("", [o["option_text"] for o in poll_opts], index=None, label_visibility="collapsed")
                if sel:
                    opt_id = next(o["id"] for o in poll_opts if o["option_text"]==sel)
                    if st.button("Submit Vote →", type="primary"):
                        record_agenda_vote(edition_id, key, opt_id, st.session_state.staff_name)
                        st.success("Vote recorded ✓"); time.sleep(0.5); st.rerun()

    # Comments
    st.markdown('<div class="section-label">💬 Comments & Feedback</div>', unsafe_allow_html=True)
    with st.form(f"agenda_comment_{key}"):
        ctxt = st.text_area("Leave a comment", height=90,
                            placeholder="Any questions or thoughts about this agenda item?",
                            label_visibility="collapsed")
        if st.form_submit_button("Post Comment"):
            if ctxt.strip():
                save_agenda_comment(edition_id, key, st.session_state.staff_name, ctxt.strip())
                st.success("Comment saved ✓"); time.sleep(0.5); st.rerun()
    if comments:
        for c in comments:
            st.markdown(f'<div class="comment-card"><div class="comment-author">{c["author"]}</div><div class="comment-body">{c["content"]}</div><div class="comment-time">{fmt_date(c["created_at"])}</div></div>', unsafe_allow_html=True)
    else:
        st.caption("No comments yet.")

    # Acknowledgement
    st.markdown('<div class="section-label">✅ Acknowledgement</div>', unsafe_allow_html=True)
    if acked:
        st.success(f"✅ You have acknowledged this agenda item.")
    else:
        st.markdown('<div class="ack-box"><h3>Acknowledge this Item</h3><p>Confirm you have read and noted this standing agenda item.</p></div>', unsafe_allow_html=True)
        st.write("")
        if st.checkbox(f"I have read and noted {label}"):
            if st.button("✓ Acknowledge", type="primary"):
                record_agenda_ack(edition_id, key, st.session_state.staff_name)
                st.success("Acknowledged ✓"); time.sleep(1); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# SUBMIT FOR NEXT WEEK  — locked after Monday COB for staff; always open for admin
# ══════════════════════════════════════════════════════════════════════════════
def show_submit():
    app_header()
    nav_bar("submit")

    edition = get_or_create_current_edition()
    if not edition:
        st.error("Could not load current edition. Please try again.")
        return

    monday = get_edition_monday(edition)
    locked = is_submission_locked(edition)

    # ── Just submitted confirmation ───────────────────────────────────────────
    if st.session_state.get("just_submitted"):
        title_added = st.session_state.pop("just_submitted")
        st.success(f"✅ **\"{title_added}\"** has been added to the draft and will appear in the meeting once published.")

    # ── STAFF: locked view ────────────────────────────────────────────────────
    if locked and not st.session_state.is_admin:
        st.markdown(f"""
        <div style="background:var(--navy-light);border:2px solid var(--navy-border);border-radius:var(--radius-lg);padding:20px 24px;margin-bottom:20px;">
          <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:var(--navy-mid);margin-bottom:4px;">📌 Submissions for</div>
          <div style="font-size:24px;font-weight:700;color:var(--ink);">{edition["week_label"]}</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("""
        <div class="locked-banner">
          <div class="lb-icon">🔒</div>
          <h3>Submissions are now closed</h3>
          <p>
            The deadline for adding agenda items was <strong>Monday COB</strong>.
            The admin team will review submissions today (Tuesday) and publish the
            meeting by Wednesday morning — you'll receive an email when it's live.<br><br>
            If you have an <strong>extraordinary reason</strong> for a late addition,
            please speak directly with admin who can add or amend items at any time.
          </p>
        </div>""", unsafe_allow_html=True)
        return

    # ── Week banner ───────────────────────────────────────────────────────────
    today = date.today()
    if monday:
        days_to_mon = (monday - today).days
        if locked:
            deadline_text = f"Staff submissions closed (Monday COB passed). Admin can still add or amend."
            banner_color = "var(--navy-light)"; border_color = "var(--navy-border)"; text_color = "var(--navy)"
        elif days_to_mon == 0:
            deadline_text = f"⏰ Today is the last day to submit — deadline is COB today."
            banner_color = "var(--amber-light)"; border_color = "#F59E0B"; text_color = "var(--amber)"
        else:
            deadline_text = f"Submissions close Monday {monday.strftime('%-d %b')} COB — {days_to_mon} day{'s' if days_to_mon!=1 else ''} to go."
            banner_color = "var(--amber-light)"; border_color = "#F59E0B"; text_color = "var(--amber)"

        st.markdown(f"""
        <div style="background:{banner_color};border:2px solid {border_color};border-radius:var(--radius-lg);padding:20px 24px;margin-bottom:24px;">
          <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:{text_color};margin-bottom:4px;">✏️ Preparing</div>
          <div style="font-size:24px;font-weight:700;color:var(--ink);">{edition["week_label"]}</div>
          <div style="font-size:13px;color:{text_color};margin-top:4px;">{deadline_text}</div>
        </div>""", unsafe_allow_html=True)

    # ── Deadline info for staff ───────────────────────────────────────────────
    if not st.session_state.is_admin:
        st.markdown("""
        <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:var(--radius);padding:12px 18px;margin-bottom:20px;">
          <div style="font-size:13px;color:#1e40af;font-weight:600;margin-bottom:4px;">📋 Submission Guidelines</div>
          <div style="font-size:13px;color:#1e3a8a;line-height:1.6;">
            All agenda items must be submitted by <strong>Monday COB</strong>.
            After this time, the agenda is locked for staff review by admin.<br>
            If you have an extraordinary reason to add something after the Monday deadline,
            please speak directly with admin.
          </div>
        </div>""", unsafe_allow_html=True)

    # ── STANDING AGENDA SECTIONS ──────────────────────────────────────────────
    # Always visible — everyone can add to standing sections (WHS, Finance, PAC etc.)
    st.markdown('<div class="section-label">📌 Standing Agenda Items</div>', unsafe_allow_html=True)
    st.caption("Click any section to add or view entries — these appear in the meeting alongside general notices.")

    if st.session_state.get("draft_agenda_view"):
        # Detail view for a standing section
        edition_id, key = st.session_state.draft_agenda_view
        label = next((l for k,l,_ in AGENDA_SECTIONS if k==key), key)

        if st.button("← Back to Agenda Sections"):
            st.session_state.draft_agenda_view = None; st.rerun()

        items     = get_agenda_items(edition_id)
        sec_items = [it for it in items if it["section"]==key]

        st.markdown(f"""
        <div class="flow-top">
          <div class="flow-title">{label}</div>
          <div class="flow-meta">Standing Agenda — {edition["week_label"]}</div>
        </div>
        <div class="flow-body">""", unsafe_allow_html=True)

        if sec_items:
            for it in sec_items:
                c1, c2 = st.columns([10, 1])
                with c1:
                    st.markdown(f'<div class="agenda-entry"><div class="agenda-entry-author">📝 {it["author"]} · {fmt_date(it["created_at"])}</div>{it["content"]}</div>', unsafe_allow_html=True)
                with c2:
                    if st.session_state.is_admin:
                        if st.button("🗑", key=f"del_agenda_{it['id']}", help="Delete this entry"):
                            st.session_state[f"confirm_del_agenda_{it['id']}"] = True
                if st.session_state.get(f"confirm_del_agenda_{it['id']}"):
                    st.warning("Delete this entry?")
                    dc1, dc2 = st.columns(2)
                    with dc1:
                        if st.button("Yes, delete", key=f"cda_{it['id']}", type="primary"):
                            # Note: deletion requires a delete function in database.py
                            st.info("Contact admin to delete entries from the database directly.")
                            st.session_state.pop(f"confirm_del_agenda_{it['id']}", None)
                    with dc2:
                        if st.button("Cancel", key=f"cxa_{it['id']}"):
                            st.session_state.pop(f"confirm_del_agenda_{it['id']}", None); st.rerun()
                st.markdown('<hr>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="agenda-empty" style="font-size:15px;padding:12px 0;">Nothing added yet — be the first to add an entry below.</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
        st.write("")

        with st.form(f"draft_agenda_add_{key}"):
            st.markdown(f"**Add an entry to {label}**")
            draft_placeholder = "Paste a link to the current timetable (e.g. Google Drive URL), or type timetable notes/changes here…" if key == "timetable" else f"Type your update for {label} here…"
            txt = st.text_area("Your update", height=120,
                               placeholder=draft_placeholder,
                               label_visibility="collapsed")
            if st.form_submit_button("✓ Save Entry", type="primary", use_container_width=True):
                if txt.strip():
                    save_agenda_item(edition_id, key, st.session_state.staff_name, txt.strip())
                    st.success("Saved ✓"); time.sleep(0.5); st.rerun()
                else:
                    st.error("Please enter some text.")

    else:
        # Grid of all standing sections
        items = get_agenda_items(edition["id"])
        by_sec = {key: [] for key, _, _ in AGENDA_SECTIONS}
        for it in items:
            if it["section"] in by_sec:
                by_sec[it["section"]].append(it)

        cols = st.columns(6)
        for i, (key, label, _) in enumerate(AGENDA_SECTIONS):
            sec_items = by_sec.get(key, [])
            has = len(sec_items) > 0
            with cols[i]:
                content_html = ""
                if has:
                    for it in sec_items[:2]:
                        content_html += f'<div class="agenda-entry"><div class="agenda-entry-author">{it["author"]}</div>{it["content"][:80]}{"…" if len(it["content"])>80 else ""}</div>'
                    if len(sec_items) > 2:
                        content_html += f'<div style="font-size:11px;color:var(--navy-mid);font-weight:600">+{len(sec_items)-2} more</div>'
                else:
                    content_html = '<div class="agenda-empty">Nothing added yet.</div>'

                st.markdown(f"""
                <div class="agenda-card {'has-content' if has else ''}">
                  <div class="agenda-section-label {'has-content' if has else ''}">{label}</div>
                  {content_html}
                </div>""", unsafe_allow_html=True)

                btn_label = "View / Edit →" if has else "Add entry →"
                if st.button(btn_label, key=f"draft_sec_{key}", use_container_width=True,
                             type="primary" if not has else "secondary"):
                    st.session_state.draft_agenda_view = (edition["id"], key); st.rerun()

    # ── Stop here if in agenda detail view ───────────────────────────────────
    if st.session_state.get("draft_agenda_view"):
        return

    st.write("")

    # ── ADMIN: draft review & publish ─────────────────────────────────────────
    if st.session_state.is_admin:
        _show_draft_panel()
        st.write("")

    # ── GENERAL NOTICES form ──────────────────────────────────────────────────
    st.markdown('<div class="section-label">📋 Add a General Notice</div>', unsafe_allow_html=True)

    with st.form("create_form", clear_on_submit=False):
        c1,c2 = st.columns(2)
        with c1:
            category = st.selectbox("Category", list(CAT_LABELS.keys()), format_func=lambda x: CAT_LABELS[x])
        with c2:
            audience = st.selectbox("Audience", ["All Staff","Junior Primary Team","Primary Years Team","Senior Years Team","Leadership"])

        title   = st.text_input("Title *", placeholder="e.g. Updated Behaviour Procedure")
        content = st.text_area("Content *", placeholder="Write your notice here…", height=160)
        author  = st.text_input("Posted By", value=st.session_state.staff_name)

        st.markdown("---")
        st.markdown("**📎 Attachments**")
        uploaded_files = st.file_uploader("Attach files", accept_multiple_files=True, label_visibility="collapsed")

        st.markdown("---")
        st.markdown("**📋 Action Items**")
        inc_actions = st.checkbox("Include action items")
        actions = []
        if inc_actions:
            for i in range(int(st.number_input("Number", 1, 8, 2, key="na"))):
                a = st.text_input(f"Action {i+1}", key=f"act_{i}")
                if a.strip(): actions.append(a.strip())

        st.markdown("---")
        st.markdown("**📊 Poll**")
        inc_poll = st.checkbox("Include a poll")
        poll_q, poll_opts = "", []
        if inc_poll:
            poll_q = st.text_input("Poll question")
            for i in range(int(st.number_input("Options", 2, 6, 3, key="npo"))):
                o = st.text_input(f"Option {i+1}", key=f"po_{i}")
                if o.strip(): poll_opts.append(o.strip())

        st.markdown("---")
        st.markdown("**💬 Feedback**")
        inc_comments = st.checkbox("Request comments", value=True)
        comment_prompt = ""
        if inc_comments:
            comment_prompt = st.text_input("Prompt", value="Do you have any questions or feedback?")

        st.markdown("---")
        submitted = st.form_submit_button("Add to This Week's Draft →", type="primary", use_container_width=True)
        if submitted:
            if not title.strip(): st.error("Please enter a title.")
            elif not content.strip(): st.error("Please enter content.")
            else:
                nid = create_notice(
                    edition_id=edition["id"], title=title.strip(), content=content.strip(),
                    category=category, author=author.strip() or st.session_state.staff_name,
                    audience=audience, has_actions=inc_actions and len(actions)>0, actions=actions,
                    has_poll=inc_poll and len(poll_opts)>=2, poll_question=poll_q, poll_options=poll_opts,
                    has_comments=inc_comments, comment_prompt=comment_prompt,
                    uploaded_files=list(uploaded_files) if uploaded_files else None
                )
                if nid:
                    st.session_state["just_submitted"] = title.strip()
                    st.success("✅ Item added to the draft! It will appear in this week's meeting once published.")
                    time.sleep(2.5); nav("submit")
                else:
                    st.error("Something went wrong. Please check your connection.")

# ══════════════════════════════════════════════════════════════════════════════
# ARCHIVE
# ══════════════════════════════════════════════════════════════════════════════
def show_archive():
    app_header()
    nav_bar("archive")
    st.markdown('<div class="page-heading">Meeting <span class="accent">Archive</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Browse and re-read all past weekly meetings.</div>', unsafe_allow_html=True)

    editions = get_all_editions()
    if not editions: st.info("No editions yet."); return

    for ed in editions:
        notices = get_notices_for_edition(ed["id"])
        status  = ed.get("status","draft")
        col1,col2 = st.columns([5,1])
        with col1:
            ack_count = sum(1 for n in notices if has_acknowledged(n["id"], st.session_state.staff_name))
            st.markdown(f"""
            <div class="edition-card">
              <div class="edition-title">{ed["week_label"]}</div>
              <div class="edition-meta">
                <span class="badge badge-{'done' if status=='published' else 'pending'}">{status.upper()}</span>
                &nbsp;{len(notices)} notice{'s' if len(notices)!=1 else ''}
                {(' · Published '+fmt_date(ed.get('published_at'))) if ed.get('published_at') else ''}
                &nbsp;· Your acknowledgements: {ack_count}/{len(notices)}
              </div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.write("")
            if status=="published":
                if st.button("View →", key=f"arch_{ed['id']}", use_container_width=True):
                    nav("archive_week", edition_id=ed["id"])
        st.write("")

def show_archive_week():
    app_header()
    ed = get_edition(st.session_state.viewing_edition_id)
    if not ed: nav("archive"); return
    if st.button("← Back to Archive"): nav("archive")
    st.markdown(f'<div class="page-heading"><span class="accent">{ed["week_label"]}</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-sub">Published {fmt_date(ed.get("published_at"))} · {ed.get("published_by","")}</div>', unsafe_allow_html=True)

    # ── Team meeting minutes cross-reference ──────────────────────────────────
    week_start = ed.get("week_start", "")
    st.markdown(f"""
    <div style="background:var(--navy-light);border:1px solid var(--navy-border);border-radius:var(--radius);
                padding:14px 18px;margin-bottom:20px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;">
      <div>
        <div style="font-size:13px;font-weight:700;color:var(--navy);">📋 Formal Staff Meeting Minutes</div>
        <div style="font-size:12px;color:var(--ink-light);margin-top:2px;">
          View formal minutes recorded for this week in the Team Meetings app
        </div>
      </div>
      <a href="https://teammeetings.streamlit.app/?program=STAFF&week={week_start}" target="_blank"
         style="background:var(--navy);color:white;padding:8px 16px;border-radius:8px;
                font-size:13px;font-weight:600;text-decoration:none;white-space:nowrap;">
        View Minutes ↗
      </a>
    </div>""", unsafe_allow_html=True)

    # ── Standing agenda items ─────────────────────────────────────────────────
    st.markdown('<div class="section-label">📌 Standing Agenda Items</div>', unsafe_allow_html=True)
    items = get_agenda_items(ed["id"])
    by_sec = {}
    for it in items:
        by_sec.setdefault(it["section"], []).append(it)

    cols = st.columns(6)
    for i, (key, label, _) in enumerate(AGENDA_SECTIONS):
        sec_items = [it for it in by_sec.get(key, []) if not it["content"].startswith("TIMETABLE_PATH::")]
        atts = get_agenda_attachments(ed["id"], key)
        has = len(sec_items) > 0 or len(atts) > 0
        with cols[i]:
            content_html = ""
            if sec_items:
                for it in sec_items[:2]:
                    content_html += f'<div class="agenda-entry"><div class="agenda-entry-author">{it["author"]}</div>{it["content"][:80]}{"…" if len(it["content"])>80 else ""}</div>'
            elif atts:
                content_html = f'<div class="agenda-entry">📎 {len(atts)} document(s)</div>'
            else:
                content_html = '<div class="agenda-empty">Nothing to report.</div>'
            st.markdown(f"""
            <div class="agenda-card {'has-content' if has else ''}">
              <div class="agenda-section-label {'has-content' if has else ''}">{label}</div>
              {content_html}
            </div>""", unsafe_allow_html=True)
            if has:
                if st.button("View →", key=f"arch_sec_{key}_{ed['id']}", use_container_width=True):
                    st.session_state.agenda_view = (ed["id"], key); st.rerun()

    if st.session_state.get("agenda_view"):
        _show_agenda_detail(ed["id"], st.session_state.agenda_view)
        return

    # ── General notices ───────────────────────────────────────────────────────
    notices = get_notices_for_edition(ed["id"])
    if notices:
        st.markdown('<div class="section-label">📋 Notices & Updates</div>', unsafe_allow_html=True)
    if not notices:
        st.info("No notices in this edition.")
        return
    for n in notices:
        cat  = n.get("category","general")
        ackd = has_acknowledged(n["id"], st.session_state.staff_name)
        st.markdown(f'<div class="card {cat}"><div class="card-meta"><span class="badge badge-{cat}">{CAT_LABELS.get(cat,cat)}</span><span class="badge {"badge-done" if ackd else "badge-pending"}">{"✓ Acknowledged" if ackd else "⚠ Pending"}</span><span>by {n.get("author","")}</span></div><div class="card-title">{n["title"]}</div></div>', unsafe_allow_html=True)
        bc1,bc2 = st.columns([2,1])
        with bc1:
            if st.button("Read →" if not ackd else "✓ Read Again", key=f"ar_{n['id']}", type="primary" if not ackd else "secondary"):
                record_read(n["id"], st.session_state.staff_name)
                st.session_state.viewing_edition_id = ed["id"]
                nav("read", notice_id=n["id"])
        with bc2:
            if st.button("Responses", key=f"arr_{n['id']}"): nav("responses", notice_id=n["id"])
        st.write("")

# ══════════════════════════════════════════════════════════════════════════════
# READ FLOW
# ══════════════════════════════════════════════════════════════════════════════
def show_read():
    app_header()
    nid = st.session_state.current_notice_id
    if not nid: nav("meeting"); return
    n = get_notice(nid)
    if not n: st.error("Notice not found."); return

    back = "← Back to Archive" if st.session_state.viewing_edition_id else "← Back to Meeting"
    back_view = "archive_week" if st.session_state.viewing_edition_id else "meeting"
    if st.button(back): nav(back_view)

    actions  = get_actions(nid)
    poll_opts= get_poll_options(nid)
    atts     = get_attachments(nid)

    steps = ["read"]
    if atts:    steps.append("attachments")
    if n.get("has_actions") and actions: steps.append("actions")
    if n.get("has_poll") and poll_opts:  steps.append("poll")
    if n.get("has_comments"): steps.append("comment")
    steps.append("ack")

    step_names = {"read":"Read","attachments":"Files","actions":"Actions","poll":"Poll","comment":"Feedback","ack":"Sign Off"}
    cur   = min(st.session_state.flow_step, len(steps)-1)
    total = len(steps)

    prog = '<div class="progress-row">'
    for i,s in enumerate(steps):
        dc = "done" if i<cur else ("active" if i==cur else "")
        prog += f'<div style="display:flex;flex-direction:column;align-items:center;gap:2px"><div class="pdot {dc}">{"✓" if i<cur else i+1}</div><div class="plabel">{step_names[s]}</div></div>'
        if i<len(steps)-1: prog += f'<div class="pline {"done" if i<cur else ""}"></div>'
    prog += '</div>'
    st.markdown(prog, unsafe_allow_html=True)

    cat = n.get("category","general")
    st.markdown(f"""
    <div class="flow-top">
      <div class="flow-meta">
        <span class="badge badge-{cat}">{CAT_LABELS.get(cat,cat)}</span>
        <span>{fmt_date(n.get('created_at'))} · {n.get('author','')} · {n.get('audience','All Staff')}</span>
      </div>
      <div class="flow-title">{n['title']}</div>
    </div>
    <div class="flow-body">""", unsafe_allow_html=True)

    step = steps[cur]

    if step=="read":
        st.markdown(f'<div class="content-text">{n.get("content","")}</div>', unsafe_allow_html=True)

    elif step=="attachments":
        st.markdown("#### 📎 Attached Files")
        for att in atts:
            fname = att.get("file_name","file")
            fsize = fmt_bytes(att.get("file_size"))
            storage_path = att.get("storage_path","")
            c1, c2 = st.columns([4,1])
            with c1:
                st.markdown(f'<div class="attach-item"><span style="font-size:20px">{file_icon(fname)}</span><div><div class="attach-name">{fname}</div><div class="attach-size">{fsize}</div></div></div>', unsafe_allow_html=True)
            with c2:
                if storage_path:
                    fb = get_attachment_bytes(storage_path)
                    if fb:
                        st.download_button("⬇ Download", data=fb, file_name=fname,
                                           key=f"dl_{att['id']}", use_container_width=True)
                    else:
                        st.warning("File unavailable")
                        if st.session_state.is_admin:
                            st.caption(f"Path: `{storage_path}`")
                else:
                    st.warning("No file path")
                    if st.session_state.is_admin:
                        st.caption(f"Attachment record: {att}")

    elif step=="actions":
        st.markdown("#### 📋 Action Items")
        st.caption("Please read and note each action item.")
        for i,a in enumerate(actions):
            st.checkbox(a["action_text"], key=f"ac_{nid}_{i}")

    elif step=="poll":
        st.markdown(f"#### 📊 {n.get('poll_question','Poll')}")
        already = has_voted(nid, st.session_state.staff_name) or st.session_state.poll_voted
        if already:
            votes=get_poll_votes(nid); total_v=sum(votes.values()) or 1
            for opt in poll_opts:
                v=votes.get(opt["id"],0); pct=round(v/total_v*100)
                st.markdown(f'<div class="poll-label"><span>{opt["option_text"]}</span><span>{v} ({pct}%)</span></div><div class="poll-bar-bg"><div class="poll-bar-fill" style="width:{pct}%"></div></div>', unsafe_allow_html=True)
            st.caption(f"Total: {sum(votes.values())}")
        else:
            sel=st.radio("", [o["option_text"] for o in poll_opts], index=None, label_visibility="collapsed")
            if sel:
                if st.button("Submit Vote →", type="primary"):
                    record_poll_vote(nid, next(o["id"] for o in poll_opts if o["option_text"]==sel), st.session_state.staff_name)
                    st.session_state.poll_voted=True; st.success("Vote recorded ✓"); time.sleep(0.8); st.rerun()

    elif step=="comment":
        st.markdown(f"#### 💬 {n.get('comment_prompt') or 'Any feedback?'}")
        comment=st.text_area("", placeholder="Your thoughts…", height=110, label_visibility="collapsed")
        if st.button("Save Comment"):
            if comment.strip(): record_comment(nid, st.session_state.staff_name, comment.strip()); st.success("Saved ✓")
            else: st.info("No comment entered — that's fine.")

    elif step=="ack":
        already_ackd=has_acknowledged(nid, st.session_state.staff_name)
        if already_ackd:
            st.success(f"✅ You've already acknowledged this notice.")
            if st.button("← Back to Meeting", type="primary"): nav("meeting")
        else:
            st.markdown('<div class="ack-box"><h3>Acknowledge this Notice</h3><p>Confirm you have read and understood this notice.</p></div>', unsafe_allow_html=True)
            st.write("")
            nc=st.text_input("Confirm your name", value=st.session_state.staff_name)
            if st.checkbox("I have read and understood this notice"):
                if st.button("✓ Submit Acknowledgement", type="primary", use_container_width=True):
                    record_acknowledgement(nid, nc or st.session_state.staff_name)
                    st.success("✅ Acknowledged. Thank you!"); time.sleep(1.5); nav("meeting")

    st.markdown('</div>', unsafe_allow_html=True)
    st.write("")

    nb1,nb2,nb3=st.columns([1,2,1])
    with nb1:
        if cur>0 and st.button("← Previous", use_container_width=True):
            st.session_state.flow_step-=1; st.rerun()
    with nb2:
        st.markdown(f'<div style="text-align:center;color:var(--ink-faint);font-size:13px;padding-top:10px">Step {cur+1} of {total}</div>', unsafe_allow_html=True)
    with nb3:
        if cur<total-1 and st.button("Continue →", type="primary", use_container_width=True):
            st.session_state.flow_step+=1; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# RESPONSES  (admin only)
# ══════════════════════════════════════════════════════════════════════════════
def show_responses():
    app_header()
    nid=st.session_state.current_notice_id
    n=get_notice(nid)
    if not n: st.error("Notice not found."); return
    if st.button("← Back"): nav("meeting")

    st.markdown(f'<div class="page-heading">{n["title"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-sub">{n.get("audience","All Staff")} · {fmt_date(n.get("created_at"))} · by {n.get("author","")}</div>', unsafe_allow_html=True)

    responses=get_responses(nid); ackd=[r for r in responses if r.get("acknowledged_at")]
    read_list=[r for r in responses if r.get("read_at")]; comments=get_comments(nid)
    poll_votes=get_poll_votes(nid); total_v=sum(poll_votes.values())

    c1,c2,c3,c4=st.columns(4)
    for col,num,lab in [(c1,len(ackd),"Acknowledged"),(c2,len(read_list),"Opened"),(c3,total_v,"Poll Votes"),(c4,len(comments),"Comments")]:
        with col: st.markdown(f'<div class="stat-card"><div class="stat-num">{num}</div><div class="stat-lab">{lab}</div></div>', unsafe_allow_html=True)
    st.write("")

    ackd_names={r.get("staff_name") for r in ackd}; read_names={r.get("staff_name") for r in read_list}
    pending=read_names-ackd_names
    if pending: st.warning(f"⏳ Opened but not yet acknowledged: {', '.join(sorted(pending))}")

    if responses:
        st.markdown("### Staff Responses")
        df=pd.DataFrame([{"Staff Member":r.get("staff_name",""),"Opened":"✓" if r.get("read_at") else "—","Acknowledged":"✓" if r.get("acknowledged_at") else "⏳","Acknowledged At":fmt_date(r.get("acknowledged_at")) if r.get("acknowledged_at") else "—","Commented":"✓" if any(c["staff_name"]==r.get("staff_name") for c in comments) else "—"} for r in responses])
        st.dataframe(df, use_container_width=True, hide_index=True)

    if n.get("has_poll") and total_v>0:
        st.markdown("---\n### 📊 Poll Results")
        st.markdown(f"**{n.get('poll_question','')}**")
        for opt in get_poll_options(nid):
            v=poll_votes.get(opt["id"],0); pct=round(v/total_v*100) if total_v else 0
            st.markdown(f'<div class="poll-label"><span>{opt["option_text"]}</span><span>{v} ({pct}%)</span></div><div class="poll-bar-bg"><div class="poll-bar-fill" style="width:{pct}%"></div></div>', unsafe_allow_html=True)
        st.caption(f"Total: {total_v}")

    if comments:
        st.markdown("---\n### 💬 Comments")
        for c in comments:
            st.markdown(f'<div class="comment-card"><div class="comment-author">{c.get("staff_name","")}</div><div class="comment-body">{c.get("comment_text","")}</div><div class="comment-time">{fmt_date(c.get("created_at",""))}</div></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# STAFF MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
def show_staff():
    app_header()
    nav_bar("staff")
    if not st.session_state.is_admin: st.error("⛔ Admins only."); return

    st.markdown('<div class="page-heading">Staff <span class="accent">Management</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Add staff, manage PINs and roles, and test email notifications.</div>', unsafe_allow_html=True)

    staff=get_staff_list()

    with st.expander("➕ Add New Staff Member", expanded=len(staff)==0):
        with st.form("add_staff"):
            c1,c2=st.columns(2)
            with c1:
                nn=st.text_input("Full Name *"); nr=st.selectbox("Role",["staff","admin"])
            with c2:
                ne=st.text_input("School Email *"); np=st.text_input("Initial PIN *",type="password",help="Min 4 characters")
            if st.form_submit_button("Add Staff Member", type="primary"):
                if not nn.strip(): st.error("Name required.")
                elif not ne.strip() or "@" not in ne: st.error("Valid email required.")
                elif len(np.strip())<4: st.error("PIN must be at least 4 characters.")
                else:
                    if add_staff_member(nn.strip(),ne.strip(),np.strip(),nr):
                        st.success(f"✅ {nn} added. Share their PIN privately."); time.sleep(0.8); st.rerun()

    st.write("")
    st.markdown(f"### Active Staff ({len(staff)})")
    if not staff: st.info("No staff added yet."); return

    for s in staff:
        c1,c2,c3,c4,c5=st.columns([3,3,1,1,1])
        with c1:
            rb='<span class="badge badge-policy" style="margin-left:6px">Admin</span>' if s.get("role")=="admin" else ""
            st.markdown(f'<span style="font-weight:600;font-size:14px">{s["name"]}</span>{rb}', unsafe_allow_html=True)
        with c2: st.markdown(f'<span style="color:var(--ink-faint);font-size:13px">{s["email"]}</span>', unsafe_allow_html=True)
        with c3: st.markdown(f'<span style="font-size:12px">{"✅ PIN set" if s.get("pin_hash") else "⚠ No PIN"}</span>', unsafe_allow_html=True)
        with c4:
            if st.button("Reset PIN", key=f"reset_{s['id']}"): st.session_state[f"resetting_{s['id']}"]=True
        with c5:
            if st.button("Remove", key=f"rm_{s['id']}"): st.session_state[f"confirm_remove_{s['id']}"]=True

        if st.session_state.get(f"confirm_remove_{s['id']}"):
            st.warning(f"Remove **{s['name']}**? History is kept.")
            rc1,rc2=st.columns(2)
            with rc1:
                if st.button("Yes, remove", key=f"crm_{s['id']}", type="primary"): remove_staff_member(s["id"]); st.session_state.pop(f"confirm_remove_{s['id']}",None); st.rerun()
            with rc2:
                if st.button("Cancel", key=f"cncrm_{s['id']}"): st.session_state.pop(f"confirm_remove_{s['id']}",None); st.rerun()

        if st.session_state.get(f"resetting_{s['id']}"):
            with st.form(f"pf_{s['id']}"):
                np2=st.text_input(f"New PIN for {s['name']}",type="password",placeholder="Min 4 chars")
                pfc1,pfc2=st.columns(2)
                with pfc1:
                    if st.form_submit_button("Set PIN", type="primary"):
                        if len(np2.strip())<4: st.error("Min 4 characters.")
                        else:
                            set_staff_pin(s["id"],np2.strip()); st.success(f"✅ PIN updated for {s['name']}."); st.session_state.pop(f"resetting_{s['id']}",None); time.sleep(0.8); st.rerun()
                with pfc2:
                    if st.form_submit_button("Cancel"): st.session_state.pop(f"resetting_{s['id']}",None); st.rerun()
        st.divider()

    st.markdown("---\n### 🔑 Change Your Own PIN")
    with st.form("own_pin"):
        op1,op2=st.columns(2)
        with op1: cur_pin=st.text_input("Current PIN",type="password")
        with op2: new_pin=st.text_input("New PIN",type="password",placeholder="Min 4 characters")
        if st.form_submit_button("Update My PIN"):
            if not verify_pin(st.session_state.staff_name, cur_pin): st.error("Current PIN is incorrect.")
            elif len(new_pin.strip())<4: st.error("New PIN must be at least 4 characters.")
            else:
                if set_staff_pin(st.session_state.staff_id, new_pin.strip()): st.success("✅ PIN updated.")

    st.markdown("---\n### 📆 Pre-create Term Weeks")
    st.caption("Creates a draft edition for every school week in 2026 that doesn't already exist. This ensures you can open any week, add content, and publish whenever you like — even weeks where no submissions came in.")
    if st.button("🗓 Seed All 2026 School Weeks", use_container_width=True):
        n_created = seed_term_weeks()
        if n_created > 0:
            st.success(f"✅ Created {n_created} new draft week(s). You'll now see them all in the Archive.")
        else:
            st.info("All term weeks already exist — nothing to create.")

    st.markdown("---\n### 📅 Current Timetable")
    st.caption("Upload the latest timetable PDF here. It will immediately appear for all staff in the Timetable agenda section.")

    timetable_record = get_global_timetable()
    if timetable_record:
        col1, col2 = st.columns([3,1])
        with col1:
            updated = fmt_date(timetable_record.get("updated_at",""))
            st.markdown(f"""
            <div style="background:var(--green-light);border:1px solid #6ee7b7;border-radius:10px;padding:12px 16px;">
              <div style="font-size:13px;font-weight:700;color:var(--green);">✅ Current timetable: {timetable_record.get('meta','timetable.pdf')}</div>
              <div style="font-size:12px;color:var(--ink-light);margin-top:3px;">Uploaded {updated} by {timetable_record.get('updated_by','admin')}</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            pdf = get_global_timetable_bytes()
            if pdf:
                st.download_button("⬇ Download", data=pdf,
                    file_name=timetable_record.get("meta","timetable.pdf"),
                    mime="application/pdf", use_container_width=True)
    else:
        st.info("No timetable uploaded yet.")

    with st.expander("📤 Upload New Timetable PDF", expanded=timetable_record is None):
        with st.form("timetable_upload_form"):
            t_file = st.file_uploader("Choose PDF", type=["pdf"], label_visibility="collapsed")
            if st.form_submit_button("✓ Save as Current Timetable", type="primary", use_container_width=True):
                if t_file:
                    import base64
                    t_file.seek(0)
                    t_bytes = t_file.read()
                    t_b64 = base64.b64encode(t_bytes).decode("utf-8")
                    if save_global_timetable(t_file.name, t_b64, st.session_state.staff_name):
                        st.success(f"✅ Timetable updated: {t_file.name}")
                        time.sleep(0.8); st.rerun()
                else:
                    st.error("Please choose a PDF file first.")

    st.markdown("---\n### 📧 Test Email")
    st.caption("Send a test to verify your SMTP settings.")
    if st.button("Send Test Email to All Staff"):
        emails=[s["email"] for s in staff]
        ok,msg=send_edition_notification("Test Edition",len(staff),emails,st.secrets.get("APP_URL",""))
        if ok:
            st.success(msg)
        else:
            st.error(msg)
            st.code(msg, language=None)

# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.staff_name:
    show_login()
else:
    v=st.session_state.view
    if   v=="meeting":      show_meeting()
    elif v=="submit":       show_submit()
    elif v=="archive":      show_archive()
    elif v=="archive_week": show_archive_week()
    elif v=="read":         show_read()
    elif v=="responses":    show_responses()
    elif v=="staff":        show_staff()
    else:                   show_meeting()
