import streamlit as st
from supabase import create_client, Client
from datetime import date, datetime, timedelta
import json
import base64
import requests
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formatdate

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CLC Committees",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)
apply_clc_theme()

from auth import require_auth, logout_button, get_staff_name
from theme import apply_clc_theme
require_auth("CLC Committees", "🏛️")
logout_button("sidebar")

# ─── SUPABASE ─────────────────────────────────────────────────────────────────
@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
supabase = init_supabase()

# ─── COMMITTEE CONFIG ─────────────────────────────────────────────────────────
COMMITTEES = {
    "PAC": {
        "emoji": "🏛️",
        "color": "#1a2e44",
        "bg":    "#e8edf3",
        "border":"#7a9cbf",
        "desc":  "Personnel Advisory Committee",
        "password_key": "PAC_PASSWORD",
        "default_pw":   "pac2026",
        "members_default": ["Principal", "Staff Rep 1", "Staff Rep 2", "Community Rep"],
    },
    "Finance": {
        "emoji": "💰",
        "color": "#065f46",
        "bg":    "#d1fae5",
        "border":"#6ee7b7",
        "desc":  "Budget · Expenditure · Financial Reports",
        "password_key": "FINANCE_PASSWORD",
        "default_pw":   "finance2026",
        "members_default": ["Principal", "Finance Officer", "Staff Rep 1", "Staff Rep 2"],
    },
    "WHS": {
        "emoji": "🦺",
        "color": "#92400e",
        "bg":    "#fef3c7",
        "border":"#fcd34d",
        "desc":  "Safety · Hazards · Compliance",
        "password_key": "WHS_PASSWORD",
        "default_pw":   "whs2026",
        "members_default": ["Principal", "WHS Officer", "Staff Rep 1", "Staff Rep 2"],
    },
    "Social Club": {
        "emoji": "🎉",
        "color": "#7c3aed",
        "bg":    "#ede9fe",
        "border":"#c4b5fd",
        "desc":  "Events · Activities · Staff Wellbeing",
        "password_key": "SOCIAL_PASSWORD",
        "default_pw":   "social2026",
        "members_default": ["Social Club Lead", "Staff Rep 1", "Staff Rep 2", "Staff Rep 3"],
    },
}

ADMIN_PASSWORD_KEY = "COMMITTEE_ADMIN_PASSWORD"
ADMIN_DEFAULT_PW   = "clcadmin2026"

# ─── DfE MEETING STRUCTURE ────────────────────────────────────────────────────
DFE_AGENDA_SECTIONS = [
    "Welcome & Opening",
    "Attendance & Apologies",
    "Confirmation of Previous Minutes",
    "Business Arising from Previous Minutes",
    "Agenda Items",
    "Other Business",
    "Date of Next Meeting",
    "Close",
]

# ─── STYLES ──────────────────────────────────────────────────────────────────

# ─── SESSION STATE ────────────────────────────────────────────────────────────
today = date.today()

# Read ?committee= query param BEFORE setting session defaults so we never
# render the landing page when arriving directly from the portal
_qp_committee = None
try:
    _qp_committee = st.query_params.get("committee", None)
except Exception:
    try:
        _qp_committee = st.experimental_get_query_params().get("committee", [None])[0]
    except Exception:
        pass
if _qp_committee and _qp_committee not in COMMITTEES:
    _qp_committee = None

defaults = {
    "selected_committee": _qp_committee,   # pre-set from URL if present
    "auth": {},
    "is_admin": False,
    "edit_minutes_id": None,
    "ai_result": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v
# Override if URL has a committee and session hasn't been set yet to something else
if _qp_committee and st.session_state.selected_committee is None:
    st.session_state.selected_committee = _qp_committee
# Clear query param so back-button works cleanly
if _qp_committee:
    try:
        st.query_params.clear()
    except Exception:
        pass

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def get_pw(committee):
    cfg = COMMITTEES[committee]
    return st.secrets.get(cfg["password_key"], cfg["default_pw"])

def is_authed(committee):
    return st.session_state.auth.get(committee, False)

def fmt_date(d):
    if not d: return "—"
    try:
        return datetime.strptime(str(d)[:10], "%Y-%m-%d").strftime("%-d %B %Y")
    except:
        return str(d)[:10]

def fmt_time(t):
    if not t: return ""
    try: return datetime.strptime(str(t)[:5], "%H:%M").strftime("%-I:%M %p")
    except: return str(t)[:5]

def file_to_b64(uploaded_file):
    if uploaded_file is None: return None, None
    return uploaded_file.name, base64.b64encode(uploaded_file.read()).decode()

def b64_download_link(name, b64data, label="⬇ Download"):
    href = f'data:application/octet-stream;base64,{b64data}'
    return f'<a href="{href}" download="{name}" style="font-size:0.82rem;color:#1a2e44;font-weight:600;">{label} {name}</a>'

# ─── DB FUNCTIONS ─────────────────────────────────────────────────────────────

# Agenda items
def db_agenda_items(committee):
    try:
        return supabase.table("committee_agenda_items")\
            .select("*").eq("committee", committee)\
            .order("created_at").execute().data or []
    except Exception as e:
        st.error(f"Could not load agenda items: {e}")
        return []

def db_add_agenda_item(row):
    supabase.table("committee_agenda_items").insert(row).execute()

def db_update_agenda_status(item_id, status):
    supabase.table("committee_agenda_items").update({"status": status}).eq("id", item_id).execute()

def db_delete_agenda_item(item_id):
    supabase.table("committee_agenda_items").delete().eq("id", item_id).execute()

# Minutes
def db_minutes(committee):
    try:
        return supabase.table("committee_minutes")\
            .select("id,committee,meeting_date,meeting_type,chair,minutes_taker,created_at,meeting_closed_at,next_meeting_date")\
            .eq("committee", committee)\
            .order("meeting_date", desc=True).execute().data or []
    except Exception as e:
        st.error(f"Could not load minutes: {e}")
        return []

def db_get_minutes(minutes_id):
    try:
        result = supabase.table("committee_minutes").select("*").eq("id", minutes_id).execute()
        return result.data[0] if result.data else None
    except:
        return None

def db_save_minutes(row):
    supabase.table("committee_minutes").insert(row).execute()

def db_update_minutes(minutes_id, row):
    supabase.table("committee_minutes").update(row).eq("id", minutes_id).execute()

def db_delete_minutes(minutes_id):
    supabase.table("committee_minutes").delete().eq("id", minutes_id).execute()

# Scheduled meetings
def db_scheduled_meetings(committee):
    try:
        return supabase.table("committee_scheduled_meetings")\
            .select("*").eq("committee", committee)\
            .gte("meeting_date", str(today))\
            .order("meeting_date").execute().data or []
    except Exception as e:
        st.error(f"Could not load scheduled meetings: {e}")
        return []

def db_all_scheduled(committee):
    try:
        return supabase.table("committee_scheduled_meetings")\
            .select("*").eq("committee", committee)\
            .order("meeting_date", desc=True).execute().data or []
    except:
        return []

def db_save_scheduled(row):
    return supabase.table("committee_scheduled_meetings").insert(row).execute()

def db_delete_scheduled(sched_id):
    supabase.table("committee_scheduled_meetings").delete().eq("id", sched_id).execute()

# ─── COMMITTEE MEMBERS (from existing staff table) ───────────────────────────
def db_get_all_staff():
    """Load all active staff from the staff_list table."""
    try:
        result = supabase.table("staff_list")\
            .select("id,name,email")\
            .eq("active", True)\
            .order("name").execute()
        return result.data or []
    except Exception as e:
        st.error(f"Could not load staff: {e}")
        return []

def db_get_committee_membership(committee):
    """Get staff IDs assigned to this committee."""
    try:
        result = supabase.table("committee_membership")\
            .select("staff_id,member_role")\
            .eq("committee", committee).execute()
        return {r["staff_id"]: r.get("member_role","Member") for r in (result.data or [])}
    except:
        return {}

def db_set_committee_membership(committee, staff_id, member_role):
    """Add a staff member to a committee."""
    try:
        supabase.table("committee_membership").upsert({
            "committee": committee,
            "staff_id": staff_id,
            "member_role": member_role,
        }, on_conflict="committee,staff_id").execute()
    except Exception as e:
        st.error(f"Could not update membership: {e}")

def db_remove_committee_membership(committee, staff_id):
    """Remove a staff member from a committee."""
    supabase.table("committee_membership")\
        .delete().eq("committee", committee).eq("staff_id", staff_id).execute()

def db_get_members(committee):
    """Get full staff details for committee members."""
    try:
        membership = db_get_committee_membership(committee)
        if not membership:
            return []
        all_staff = db_get_all_staff()
        members = []
        for s in all_staff:
            if s["id"] in membership:
                members.append({
                    "id":    s["id"],
                    "name":  s["name"],
                    "email": s["email"],
                    "role":  membership[s["id"]],
                })
        return members
    except:
        return []

# ─── ICS CALENDAR INVITE GENERATOR ──────────────────────────────────────────
def make_ics(committee, meeting_date, meeting_time, location, meeting_type, organiser_email):
    """Generate an .ics calendar invite file."""
    try:
        # Parse start datetime
        time_str = meeting_time.strip() if meeting_time else "15:00"
        # Try to parse common time formats
        for fmt in ["%I:%M %p", "%I:%M%p", "%H:%M", "%I %p"]:
            try:
                t = datetime.strptime(time_str.upper(), fmt)
                break
            except:
                t = datetime.strptime("15:00", "%H:%M")
        dt_start = datetime.combine(meeting_date, t.time())
        dt_end = dt_start + timedelta(hours=1)

        uid = f"{committee.lower().replace(' ','-')}-{meeting_date}-{dt_start.strftime('%H%M')}@clc"
        fmt_dt = lambda d: d.strftime("%Y%m%dT%H%M%S")

        ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CLC Committees//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")}
DTSTART:{fmt_dt(dt_start)}
DTEND:{fmt_dt(dt_end)}
SUMMARY:{committee} Committee — {meeting_type} Meeting
DESCRIPTION:You are invited to the {committee} Committee {meeting_type} Meeting at Cowandilla Learning Centre.
LOCATION:{location or 'Cowandilla Learning Centre'}
ORGANIZER:MAILTO:{organiser_email}
STATUS:CONFIRMED
SEQUENCE:0
END:VEVENT
END:VCALENDAR"""
        return ics.encode("utf-8")
    except Exception as e:
        return None

# ─── EMAIL SENDING ────────────────────────────────────────────────────────────
def send_meeting_invites(committee, meeting_date, meeting_time, location,
                          meeting_type, sender_name, recipients, agenda_items=None):
    """Send meeting invite emails with ICS attachment to all recipients."""
    cfg = COMMITTEES[committee]

    # Use same [smtp] secrets format as staff meeting app
    smtp_conf  = st.secrets.get("smtp", {})
    smtp_host  = smtp_conf.get("host", "smtp.gmail.com")
    smtp_port  = int(smtp_conf.get("port", 587))
    smtp_user  = smtp_conf.get("user", "")
    smtp_pass  = smtp_conf.get("password", "")
    from_name  = smtp_conf.get("from_name", "CLC Committees")
    from_email = smtp_user

    if not smtp_user or not smtp_pass:
        st.error("⚠️ Email not configured. Add [smtp] section to your Streamlit secrets.")
        return 0, []

    date_str = fmt_date(meeting_date)
    time_str = f" at {meeting_time}" if meeting_time else ""
    loc_str  = f" — {location}" if location else ""

    # Build agenda HTML
    agenda_html = ""
    if agenda_items:
        items_html = "".join(f"<li>{item.get('title','')}</li>" for item in agenda_items if item.get('title'))
        if items_html:
            agenda_html = f"""
            <div style="margin-top:16px;">
              <strong style="color:#1a2e44;">Proposed Agenda Items:</strong>
              <ul style="margin:8px 0;padding-left:20px;color:#374151;">{items_html}</ul>
            </div>"""

    # ICS attachment
    ics_data = make_ics(committee, meeting_date, meeting_time, location, meeting_type, from_email)

    sent_to = []
    errors = []

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(smtp_user, smtp_pass)

            for recipient in recipients:
                name  = recipient.get("name","")
                email = recipient.get("email","")
                if not email or "@" not in email:
                    continue

                msg = MIMEMultipart("mixed")
                msg["From"]    = f"{sender_name} <{from_email}>"
                msg["To"]      = f"{name} <{email}>" if name else email
                msg["Subject"] = f"📅 {committee} Committee — {meeting_type} Meeting | {date_str}"
                msg["Date"]    = formatdate(localtime=True)

                html_body = f"""
<html><body style="font-family:'Segoe UI',Arial,sans-serif;color:#222;max-width:600px;margin:0 auto;">
  <div style="background:linear-gradient(135deg,{cfg['color']},{cfg['color']}cc);
              color:white;padding:24px 28px;border-radius:12px 12px 0 0;">
    <div style="font-size:2rem;">{cfg['emoji']}</div>
    <h2 style="margin:8px 0 4px;font-size:1.3rem;">{committee} Committee</h2>
    <p style="margin:0;opacity:0.85;font-size:0.9rem;">Meeting Invitation — Cowandilla Learning Centre</p>
  </div>
  <div style="background:white;border:1px solid #e5e7eb;border-top:none;
              padding:24px 28px;border-radius:0 0 12px 12px;">
    <p style="font-size:1rem;color:#374151;">Dear {name or 'Committee Member'},</p>
    <p style="color:#374151;">You are invited to the following committee meeting:</p>

    <div style="background:{cfg['bg']};border-left:4px solid {cfg['color']};
                border-radius:8px;padding:16px 20px;margin:16px 0;">
      <div style="font-size:1.1rem;font-weight:700;color:{cfg['color']};">
        {committee} Committee — {meeting_type} Meeting
      </div>
      <div style="margin-top:10px;font-size:0.95rem;color:#374151;">
        <div>📅 <strong>Date:</strong> {date_str}</div>
        {f'<div>⏰ <strong>Time:</strong> {meeting_time}</div>' if meeting_time else ''}
        {f'<div>📍 <strong>Location:</strong> {location}</div>' if location else ''}
      </div>
    </div>

    {agenda_html}

    <p style="color:#374151;margin-top:16px;">
      A calendar invite is attached. Please accept to add this to your calendar.
    </p>
    <p style="color:#374151;">
      If you are unable to attend, please send your apologies to {sender_name}.
    </p>

    <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0;">
    <p style="font-size:0.78rem;color:#9ca3af;margin:0;">
      Sent via CLC Committee Management System · Cowandilla Learning Centre
    </p>
  </div>
</body></html>"""

                msg.attach(MIMEText(html_body, "html"))

                # Attach ICS
                if ics_data:
                    ics_part = MIMEBase("text", "calendar", method="REQUEST", name="invite.ics")
                    ics_part.set_payload(ics_data)
                    encoders.encode_base64(ics_part)
                    ics_part.add_header("Content-Disposition", "attachment", filename="invite.ics")
                    msg.attach(ics_part)

                try:
                    server.sendmail(from_email, email, msg.as_string())
                    sent_to.append(f"{name} <{email}>")
                except Exception as e:
                    errors.append(f"{email}: {e}")

    except Exception as e:
        st.error(f"SMTP connection error: {e}")
        return 0, errors

    return len(sent_to), errors

# Calendar integration
def post_to_calendar(committee, meeting_date, meeting_time, location, meeting_type, added_by):
    cfg = COMMITTEES[committee]
    title = f"{committee} Committee — {meeting_type} Meeting"
    try:
        supabase.table("clc_events").insert({
            "title": title,
            "event_type": "Staff Meeting",
            "event_date": str(meeting_date),
            "start_time": meeting_time if meeting_time else None,
            "location": location or "",
            "added_by": added_by,
            "notes": f"Scheduled via {committee} Committee portal",
        }).execute()
        return True
    except Exception as e:
        st.error(f"Calendar error: {e}")
        return False

# Bulletin integration
def post_to_bulletin(committee, meeting_date, meeting_time, location, meeting_type, added_by):
    cfg = COMMITTEES[committee]
    date_str = fmt_date(meeting_date)
    time_str = f" at {fmt_time(meeting_time)}" if meeting_time else ""
    loc_str  = f" — {location}" if location else ""
    try:
        supabase.table("bulletin_notices").insert({
            "submitted_by": added_by,
            "category": "Reminder",
            "title": f"{cfg['emoji']} {committee} Committee — {meeting_type} Meeting",
            "body": f"Scheduled for {date_str}{time_str}{loc_str}",
            "notice_date": str(meeting_date),
        }).execute()
        return True
    except Exception as e:
        st.error(f"Bulletin error: {e}")
        return False

# ─── AI MINUTES ASSISTANT ─────────────────────────────────────────────────────
def ai_structure_minutes(raw_text, committee, meeting_date, mode="transcript"):
    """Use Claude API to structure raw text into DfE meeting minutes."""
    cfg = COMMITTEES[committee]
    date_str = fmt_date(meeting_date)

    if mode == "transcript":
        instruction = f"""You are helping structure a meeting transcript into formal DfE (Department for Education, South Australia) meeting minutes for the {committee} Committee at Cowandilla Learning Centre, held on {date_str}.

Extract and format the following sections from the transcript. If a section isn't clearly present, note "Not recorded" or make a reasonable inference:

1. **Attendance** — Who was present (list names/roles)
2. **Apologies** — Who sent apologies
3. **Confirmation of Previous Minutes** — Moved by / Seconded by / Carried
4. **Business Arising** — Any action items from previous minutes discussed
5. **Agenda Items** — For each item: Title, Discussion summary, Outcome/Resolution, Action required, Responsible person, Due date
6. **Other Business** — Any other matters discussed
7. **Next Meeting** — Date, time, location if mentioned
8. **Close** — Time meeting closed

Return your response as a JSON object with these exact keys:
attendance, apologies, prev_minutes_confirmed, prev_minutes_mover, prev_minutes_seconder, business_arising, agenda_items (array of objects with: title, discussion, outcome, action, responsible, due_date), other_business, next_meeting_date, next_meeting_time, next_meeting_location, meeting_closed_at

For agenda_items, return a JSON array.
Return ONLY valid JSON, no markdown, no explanation."""
    else:  # improve typed notes
        instruction = f"""You are helping improve rough meeting notes into formal DfE (Department for Education, South Australia) meeting minutes for the {committee} Committee at Cowandilla Learning Centre, held on {date_str}.

Take these rough notes and:
1. Improve grammar, clarity and professionalism
2. Structure into the formal DfE meeting format
3. Ensure all resolutions are clearly stated
4. Format action items with responsible person and due dates where mentioned

Return your response as a JSON object with these exact keys:
attendance, apologies, prev_minutes_confirmed, prev_minutes_mover, prev_minutes_seconder, business_arising, agenda_items (array of objects with: title, discussion, outcome, action, responsible, due_date), other_business, next_meeting_date, next_meeting_time, next_meeting_location, meeting_closed_at

For agenda_items, return a JSON array.
Return ONLY valid JSON, no markdown, no explanation."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4000,
                "system": instruction,
                "messages": [{"role": "user", "content": raw_text}]
            },
            timeout=60
        )
        result = response.json()
        raw = result["content"][0]["text"]
        # Strip any markdown fences
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        st.error(f"AI processing error: {e}")
        return None

# ─── LANDING PAGE ─────────────────────────────────────────────────────────────
def landing_page():
    st.markdown("""
    <div style="background:linear-gradient(135deg,#1a2e44,#2d4a6e);color:white;
                padding:1.5rem 2rem;border-radius:14px;margin-bottom:1.5rem;
                box-shadow:0 4px 20px rgba(26,46,74,0.3);">
      <div style="display:flex;align-items:center;gap:1.2rem;">
        <div style="font-size:3rem;">🏛️</div>
        <div>
          <h1 style="margin:0;font-size:1.7rem;font-weight:800;">CLC Committees</h1>
          <p style="margin:0.2rem 0 0;opacity:0.8;font-size:0.9rem;">
            Cowandilla Learning Centre — Agendas · Minutes · Scheduling
          </p>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**Select a committee to continue:**")
    col1, col2 = st.columns(2)
    cols = [col1, col2, col1, col2]
    for i, (name, cfg) in enumerate(COMMITTEES.items()):
        with cols[i]:
            st.markdown(f"""
            <div style="background:{cfg['bg']};border:2px solid {cfg['border']};
                        border-radius:14px;padding:1.5rem 1.2rem;text-align:center;
                        margin-bottom:0.5rem;">
              <div style="font-size:2.5rem;">{cfg['emoji']}</div>
              <div style="font-weight:700;color:{cfg['color']};font-size:1rem;margin-top:0.4rem;">{name}</div>
              <div style="font-size:0.78rem;color:#555;margin-top:0.3rem;">{cfg['desc']}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Enter {name}", key=f"enter_{name}", use_container_width=True, type="primary"):
                st.session_state.selected_committee = name
                st.rerun()

# ─── AUTH GATE ────────────────────────────────────────────────────────────────
def auth_gate(committee):
    cfg = COMMITTEES[committee]
    st.markdown(f"""
    <div style="background:{cfg['bg']};border:2px solid {cfg['border']};
                border-radius:14px;padding:1.5rem;max-width:400px;margin:2rem auto;text-align:center;">
      <div style="font-size:3rem;">{cfg['emoji']}</div>
      <h2 style="color:{cfg['color']};margin:0.5rem 0 0.2rem;">{committee} Committee</h2>
      <p style="color:#555;font-size:0.88rem;margin-bottom:1.2rem;">Enter the committee password to continue.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        pw = st.text_input("Password", type="password", key=f"pw_{committee}")
        if st.button("🔓 Enter", type="primary", use_container_width=True):
            if pw == get_pw(committee):
                st.session_state.auth[committee] = True
                st.rerun()
            else:
                st.error("Incorrect password.")
        if st.button("← Back to committees", use_container_width=True):
            st.session_state.selected_committee = None
            st.rerun()

# ─── AGENDA TAB ───────────────────────────────────────────────────────────────
def render_agenda_tab(committee):
    cfg = COMMITTEES[committee]
    items = db_agenda_items(committee)
    pending = [i for i in items if i.get("status","pending") == "pending"]
    discussed = [i for i in items if i.get("status","pending") != "pending"]

    # Upcoming meeting context
    upcoming = db_scheduled_meetings(committee)
    if upcoming:
        nm = upcoming[0]
        nm_date = fmt_date(nm.get("meeting_date"))
        st.markdown(f"""
        <div class="next-meeting-box" style="background:{cfg['bg']};border-color:{cfg['border']};">
          <span style="font-size:0.78rem;font-weight:700;color:{cfg['color']};text-transform:uppercase;
                       letter-spacing:0.05em;">Next Scheduled Meeting</span>
          <div style="font-size:1.1rem;font-weight:700;color:{cfg['color']};margin-top:0.2rem;">
            📅 {nm_date}
            {f"&nbsp;⏰ {fmt_time(nm.get('meeting_time'))}" if nm.get('meeting_time') else ""}
            {f"&nbsp;📍 {nm.get('location')}" if nm.get('location') else ""}
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Add new agenda item
    with st.expander("➕ Add Agenda Item", expanded=not pending):
        with st.form("agenda_add", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("Item title *", placeholder="e.g. Review of Q1 Budget")
                submitted_by = st.text_input("Submitted by *", placeholder="Your name")
            with col2:
                desc = st.text_area("Description / background", height=100,
                                    placeholder="Provide any context or information relevant to this item...")
                target_date = st.date_input("For meeting on (optional)",
                                            value=upcoming[0].get("meeting_date") if upcoming else None,
                                            key="agenda_target_date")
            upload = st.file_uploader("📎 Attach pre-reading (PDF, Word, image — max 5MB)",
                                       type=["pdf","docx","doc","png","jpg","xlsx"],
                                       key="agenda_upload")
            submitted = st.form_submit_button("➕ Add to Agenda", type="primary", use_container_width=True)
            if submitted:
                if not title.strip() or not submitted_by.strip():
                    st.warning("Title and submitter name are required.")
                else:
                    fname, fdata = file_to_b64(upload)
                    if fdata and len(fdata) > 7_000_000:
                        st.error("File too large (max ~5MB). Please compress or use a smaller file.")
                    else:
                        db_add_agenda_item({
                            "committee": committee,
                            "title": title.strip(),
                            "description": desc.strip(),
                            "submitted_by": submitted_by.strip(),
                            "target_meeting_date": str(target_date) if target_date else None,
                            "attachment_name": fname,
                            "attachment_data": fdata,
                            "status": "pending",
                        })
                        st.success(f"✅ '{title}' added to agenda!")
                        st.rerun()

    st.markdown("---")

    # Pending items
    if not pending:
        st.markdown('<div class="info-box">📭 No pending agenda items — add one above.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f"**{len(pending)} item{'s' if len(pending)!=1 else ''} pending for next meeting:**")
        for item in pending:
            with st.container():
                c1, c2, c3 = st.columns([8,1,1])
                with c1:
                    attach_html = ""
                    if item.get("attachment_name") and item.get("attachment_data"):
                        attach_html = f'<br>{b64_download_link(item["attachment_name"], item["attachment_data"], "📎")}'
                    st.markdown(f"""
                    <div class="agenda-item" style="border-left-color:{cfg['color']};">
                      <div style="font-weight:700;color:{cfg['color']};font-size:0.95rem;">{item['title']}</div>
                      {f'<div style="font-size:0.83rem;color:#444;margin-top:0.3rem;">{item["description"]}</div>' if item.get("description") else ""}
                      <div style="font-size:0.75rem;color:#888;margin-top:0.4rem;">
                        👤 {item.get('submitted_by','—')}
                        {f" · 📅 For {fmt_date(item.get('target_meeting_date'))}" if item.get('target_meeting_date') else ""}
                        {attach_html}
                      </div>
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    if st.session_state.is_admin or True:  # any authed user
                        st.write("")
                        status = st.selectbox("", ["pending","discussed","carried","noted","deferred"],
                                              index=0, key=f"status_{item['id']}",
                                              label_visibility="collapsed")
                        if status != "pending":
                            if st.button("✔ Set", key=f"setstatus_{item['id']}", use_container_width=True):
                                db_update_agenda_status(item["id"], status)
                                st.rerun()
                with c3:
                    if st.session_state.is_admin:
                        st.write("")
                        st.write("")
                        if st.button("🗑️", key=f"del_ag_{item['id']}", help="Delete item"):
                            db_delete_agenda_item(item["id"])
                            st.rerun()

    # Discussed / archived items
    if discussed:
        with st.expander(f"📂 Archive — {len(discussed)} resolved item{'s' if len(discussed)!=1 else ''}"):
            STATUS_COLORS = {
                "discussed": ("#d97706","#fef3c7"),
                "carried":   ("#065f46","#d1fae5"),
                "noted":     ("#1d4ed8","#dbeafe"),
                "deferred":  ("#6b7280","#f3f4f6"),
            }
            for item in discussed:
                s = item.get("status","discussed")
                sc, sb = STATUS_COLORS.get(s,("#374151","#f3f4f6"))
                st.markdown(f"""
                <div style="background:white;border:1px solid #e5e7eb;border-radius:8px;
                            padding:0.6rem 0.9rem;margin-bottom:0.4rem;display:flex;
                            align-items:center;gap:0.75rem;">
                  <span style="background:{sb};color:{sc};font-size:0.7rem;font-weight:700;
                               padding:0.15rem 0.5rem;border-radius:20px;">{s.upper()}</span>
                  <span style="font-weight:600;color:#1a2e44;">{item['title']}</span>
                  <span style="font-size:0.75rem;color:#888;margin-left:auto;">
                    {item.get('submitted_by','—')}
                  </span>
                </div>
                """, unsafe_allow_html=True)

# ─── MINUTES TAB ──────────────────────────────────────────────────────────────
def render_minutes_tab(committee):
    cfg = COMMITTEES[committee]
    all_minutes = db_minutes(committee)

    sub_tab_list, sub_tab_new, sub_tab_ai = st.tabs(["📋 Minutes Archive", "📝 Record New Minutes", "🤖 AI Minutes Assistant"])

    # ── Archive ──
    with sub_tab_list:
        if not all_minutes:
            st.markdown('<div class="info-box">No minutes recorded yet. Use the "Record New Minutes" tab to add your first set.</div>', unsafe_allow_html=True)
        else:
            for m in all_minutes:
                mid = m.get("id","")
                mdate = fmt_date(m.get("meeting_date"))
                mtype = m.get("meeting_type","Ordinary")
                chair = m.get("chair","")
                taker = m.get("minutes_taker","")

                c1, c2, c3 = st.columns([7,1,1])
                with c1:
                    st.markdown(f"""
                    <div class="minutes-card" style="border-left-color:{cfg['color']};">
                      <div style="font-weight:700;color:{cfg['color']};font-size:0.95rem;">
                        {cfg['emoji']} {committee} — {mtype} Meeting
                      </div>
                      <div style="font-size:0.82rem;color:#555;margin-top:0.25rem;">
                        📅 {mdate}
                        {f" · 👤 Chair: {chair}" if chair else ""}
                        {f" · 📝 Minutes: {taker}" if taker else ""}
                      </div>
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    st.write("")
                    if st.button("📄 View", key=f"view_m_{mid}", use_container_width=True):
                        st.session_state.edit_minutes_id = mid if st.session_state.edit_minutes_id != mid else None
                        st.rerun()
                with c3:
                    if st.session_state.is_admin:
                        st.write("")
                        if st.button("🗑️", key=f"del_m_{mid}", help="Delete"):
                            db_delete_minutes(mid)
                            st.rerun()

                # View/edit expanded
                if st.session_state.edit_minutes_id == mid:
                    full = db_get_minutes(mid)
                    if full:
                        render_minutes_view(full, committee, cfg)

    # ── New Minutes ──
    with sub_tab_new:
        render_new_minutes_form(committee, cfg)

    # ── AI Assistant ──
    with sub_tab_ai:
        render_ai_assistant(committee, cfg)

def render_minutes_view(m, committee, cfg):
    """Render a full set of minutes for viewing."""
    mdate = fmt_date(m.get("meeting_date"))
    st.markdown(f"""
    <div style="background:{cfg['bg']};border-radius:12px;padding:1.25rem 1.5rem;margin:0.5rem 0 1rem;">
      <h3 style="color:{cfg['color']};margin:0 0 0.2rem;">
        {cfg['emoji']} {committee} Committee — {m.get('meeting_type','Ordinary')} Meeting
      </h3>
      <div style="font-size:0.85rem;color:#555;">
        📅 {mdate}
        {f" &nbsp;📍 {m.get('location')}" if m.get('location') else ""}
      </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Chair:** {m.get('chair','—')}")
        st.markdown(f"**Minutes Taker:** {m.get('minutes_taker','—')}")
        present = m.get("members_present") or []
        if isinstance(present, str):
            try: present = json.loads(present)
            except: present = [present]
        st.markdown(f"**Present:** {', '.join(present) if present else '—'}")
    with col2:
        apologies = m.get("apologies") or []
        if isinstance(apologies, str):
            try: apologies = json.loads(apologies)
            except: apologies = [apologies]
        st.markdown(f"**Apologies:** {', '.join(apologies) if apologies else 'None'}")
        prev = "Yes" if m.get("previous_minutes_confirmed") else "Not recorded"
        mover = m.get("previous_minutes_mover","")
        seconder = m.get("previous_minutes_seconder","")
        conf_str = prev
        if mover: conf_str += f" — Moved: {mover}"
        if seconder: conf_str += f" / Seconded: {seconder}"
        st.markdown(f"**Prev Minutes Confirmed:** {conf_str}")

    if m.get("business_arising","").strip():
        st.markdown("**Business Arising:**")
        st.markdown(f"> {m['business_arising']}")

    st.markdown("**Agenda Items:**")
    agenda_items = m.get("agenda_items") or []
    if isinstance(agenda_items, str):
        try: agenda_items = json.loads(agenda_items)
        except: agenda_items = []
    for i, item in enumerate(agenda_items, 1):
        if isinstance(item, str):
            try: item = json.loads(item)
            except: item = {"title": item}
        st.markdown(f"""
        <div class="dfe-section">
          <h4>{i}. {item.get('title','Agenda Item')}</h4>
          {f'<p style="font-size:0.85rem;margin:0 0 0.3rem;"><strong>Discussion:</strong> {item.get("discussion","")}</p>' if item.get("discussion") else ""}
          {f'<p style="font-size:0.85rem;margin:0 0 0.3rem;"><strong>Outcome:</strong> {item.get("outcome","")}</p>' if item.get("outcome") else ""}
          {f'<p style="font-size:0.85rem;margin:0;color:#b91c1c;"><strong>Action:</strong> {item.get("action","")} — {item.get("responsible","")} by {item.get("due_date","")}</p>' if item.get("action") else ""}
        </div>
        """, unsafe_allow_html=True)

    if m.get("other_business","").strip():
        st.markdown("**Other Business:**")
        st.markdown(f"> {m['other_business']}")

    if m.get("next_meeting_date"):
        st.markdown(f"**Next Meeting:** {fmt_date(m['next_meeting_date'])}"
                   + (f" at {fmt_time(m.get('next_meeting_time'))}" if m.get("next_meeting_time") else "")
                   + (f" — {m.get('next_meeting_location','')}" if m.get("next_meeting_location") else ""))

    if m.get("meeting_closed_at"):
        st.markdown(f"**Meeting Closed:** {m['meeting_closed_at']}")

    # Attachments
    attachments = m.get("attachments") or []
    if isinstance(attachments, str):
        try: attachments = json.loads(attachments)
        except: attachments = []
    if attachments:
        st.markdown("**Attachments:**")
        for att in attachments:
            if att.get("name") and att.get("data"):
                st.markdown(b64_download_link(att["name"], att["data"]), unsafe_allow_html=True)

def render_new_minutes_form(committee, cfg):
    """Full DfE-structured minutes form."""
    st.markdown(f"""
    <div class="info-box">
      📋 Use this form to record meeting minutes in the DfE standard structure.
      All sections follow SA Government Department for Education requirements.
    </div>
    """, unsafe_allow_html=True)

    # Pre-fill from AI result if available
    ai = st.session_state.get("ai_result") or {}

    with st.form("new_minutes_form", clear_on_submit=False):
        st.markdown("### 📋 Meeting Details")
        r1c1, r1c2, r1c3 = st.columns(3)
        with r1c1:
            meeting_date = st.date_input("Meeting date *", value=today)
            meeting_type = st.selectbox("Meeting type", ["Ordinary","Special","Extraordinary","Annual"])
        with r1c2:
            chair = st.text_input("Chair *", value=ai.get("chair",""), placeholder="Name of chairperson")
            minutes_taker = st.text_input("Minutes taker *", value=ai.get("minutes_taker",""), placeholder="Name")
        with r1c3:
            location = st.text_input("Location", placeholder="e.g. Staff Room")
            opened_at = st.text_input("Meeting opened at", placeholder="e.g. 3:30 PM")

        st.markdown("---")
        st.markdown("### 1. Attendance & Apologies")
        r2c1, r2c2 = st.columns(2)
        with r2c1:
            default_present = ", ".join(ai.get("attendance") or []) if isinstance(ai.get("attendance"), list) else (ai.get("attendance","") or "")
            members_present_raw = st.text_area("Members present (one per line)",
                                                value=default_present,
                                                height=100, placeholder="John Smith\nJane Doe")
        with r2c2:
            default_apologies = ", ".join(ai.get("apologies") or []) if isinstance(ai.get("apologies"), list) else (ai.get("apologies","") or "")
            apologies_raw = st.text_area("Apologies (one per line)",
                                          value=default_apologies,
                                          height=100, placeholder="Sarah Jones")

        st.markdown("---")
        st.markdown("### 2. Confirmation of Previous Minutes")
        r3c1, r3c2, r3c3 = st.columns(3)
        with r3c1:
            prev_confirmed = st.checkbox("Previous minutes confirmed",
                                          value=bool(ai.get("prev_minutes_confirmed", False)))
        with r3c2:
            prev_mover = st.text_input("Moved by", value=ai.get("prev_minutes_mover",""))
        with r3c3:
            prev_seconder = st.text_input("Seconded by", value=ai.get("prev_minutes_seconder",""))

        st.markdown("---")
        st.markdown("### 3. Business Arising from Previous Minutes")
        business_arising = st.text_area("Business arising",
                                         value=ai.get("business_arising",""),
                                         height=80,
                                         placeholder="Any action items or business from the previous meeting...")

        st.markdown("---")
        st.markdown("### 4. Agenda Items")
        st.markdown('<div class="info-box">Add each agenda item separately. Include discussion notes, outcomes, and any action items.</div>', unsafe_allow_html=True)

        # Pre-fill from agenda items in database
        pending_agenda = db_agenda_items(committee)
        pending_agenda = [i for i in pending_agenda if i.get("status","pending") == "pending"]
        ai_items = ai.get("agenda_items") or []

        # Determine number of items to show
        n_items = max(len(pending_agenda), len(ai_items), 3)
        if "n_agenda_items" not in st.session_state:
            st.session_state.n_agenda_items = n_items

        agenda_items_data = []
        for idx in range(st.session_state.n_agenda_items):
            st.markdown(f"**Item {idx+1}**")
            ai_item = ai_items[idx] if idx < len(ai_items) else {}
            db_item = pending_agenda[idx] if idx < len(pending_agenda) else {}
            default_title = ai_item.get("title","") or db_item.get("title","")
            default_desc  = ai_item.get("discussion","") or db_item.get("description","")

            ic1, ic2 = st.columns([2,3])
            with ic1:
                item_title = st.text_input(f"Item title", value=default_title, key=f"ai_title_{idx}")
                item_outcome = st.text_input(f"Outcome / Resolution", value=ai_item.get("outcome",""), key=f"ai_outcome_{idx}")
            with ic2:
                item_discussion = st.text_area(f"Discussion notes", value=default_desc, height=80, key=f"ai_disc_{idx}")
                ia1, ia2, ia3 = st.columns(3)
                with ia1:
                    item_action = st.text_input("Action required", value=ai_item.get("action",""), key=f"ai_action_{idx}")
                with ia2:
                    item_responsible = st.text_input("Responsible", value=ai_item.get("responsible",""), key=f"ai_resp_{idx}")
                with ia3:
                    item_due = st.text_input("Due date", value=ai_item.get("due_date",""), key=f"ai_due_{idx}", placeholder="e.g. Term 2 Week 4")
            if item_title.strip():
                agenda_items_data.append({
                    "title": item_title.strip(),
                    "discussion": item_discussion.strip(),
                    "outcome": item_outcome.strip(),
                    "action": item_action.strip(),
                    "responsible": item_responsible.strip(),
                    "due_date": item_due.strip(),
                })
            st.markdown("<hr style='margin:0.4rem 0;border-color:#f0f0f0;'>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 5. Other Business")
        other_business = st.text_area("Other business",
                                       value=ai.get("other_business",""),
                                       height=80, placeholder="Any other matters raised...")

        st.markdown("---")
        st.markdown("### 6. Next Meeting & Close")
        r5c1, r5c2, r5c3, r5c4 = st.columns(4)
        with r5c1:
            nm_date_raw = ai.get("next_meeting_date","")
            try:
                nm_date_val = datetime.strptime(str(nm_date_raw)[:10],"%Y-%m-%d").date() if nm_date_raw else None
            except:
                nm_date_val = None
            next_meeting_date = st.date_input("Next meeting date", value=nm_date_val, key="nm_date_form")
        with r5c2:
            next_meeting_time = st.text_input("Next meeting time", value=ai.get("next_meeting_time",""), placeholder="e.g. 3:30 PM")
        with r5c3:
            next_meeting_location = st.text_input("Next meeting location", value=ai.get("next_meeting_location",""), placeholder="e.g. Staff Room")
        with r5c4:
            meeting_closed_at = st.text_input("Meeting closed at", placeholder="e.g. 4:15 PM")

        st.markdown("### 📎 Attachments")
        attachments_upload = st.file_uploader(
            "Attach files (PDFs, images, documents — max 5MB each)",
            accept_multiple_files=True,
            type=["pdf","docx","doc","png","jpg","xlsx","pptx"],
            key="minutes_attachments"
        )

        # Options
        r6c1, r6c2 = st.columns(2)
        with r6c1:
            add_to_calendar = st.checkbox("📅 Add next meeting to Communal Calendar", value=True)
        with r6c2:
            add_to_bulletin = st.checkbox("📋 Add next meeting to Daily Bulletin", value=True)
        creator_name = st.text_input("Recorded by *", placeholder="Your name")

        submitted = st.form_submit_button("💾 Save Minutes", type="primary", use_container_width=True)

        if submitted:
            if not chair.strip() or not creator_name.strip():
                st.warning("Chair and 'Recorded by' are required.")
            else:
                # Process attachments
                attachments_data = []
                for f in (attachments_upload or []):
                    fname, fdata = file_to_b64(f)
                    if fdata and len(fdata) < 7_000_000:
                        attachments_data.append({"name": fname, "data": fdata})
                    else:
                        st.warning(f"⚠ '{fname}' too large — skipped.")

                present_list = [x.strip() for x in members_present_raw.split("\n") if x.strip()]
                apologies_list = [x.strip() for x in apologies_raw.split("\n") if x.strip()]

                row = {
                    "committee": committee,
                    "meeting_date": str(meeting_date),
                    "meeting_type": meeting_type,
                    "location": location.strip(),
                    "chair": chair.strip(),
                    "minutes_taker": minutes_taker.strip(),
                    "members_present": json.dumps(present_list),
                    "apologies": json.dumps(apologies_list),
                    "previous_minutes_confirmed": prev_confirmed,
                    "previous_minutes_mover": prev_mover.strip(),
                    "previous_minutes_seconder": prev_seconder.strip(),
                    "business_arising": business_arising.strip(),
                    "agenda_items": json.dumps(agenda_items_data),
                    "other_business": other_business.strip(),
                    "next_meeting_date": str(next_meeting_date) if next_meeting_date else None,
                    "next_meeting_time": next_meeting_time.strip(),
                    "next_meeting_location": next_meeting_location.strip(),
                    "meeting_closed_at": meeting_closed_at.strip(),
                    "attachments": json.dumps(attachments_data),
                    "created_by": creator_name.strip(),
                    "raw_transcript": "",
                }
                db_save_minutes(row)

                # Mark pending agenda items as discussed
                for item in pending_agenda:
                    if any(ai.get("title","").strip().lower() == item.get("title","").strip().lower()
                           for ai in agenda_items_data):
                        db_update_agenda_status(item["id"], "discussed")

                # Calendar & Bulletin for next meeting
                if next_meeting_date:
                    if add_to_calendar:
                        post_to_calendar(committee, next_meeting_date, next_meeting_time,
                                         next_meeting_location, meeting_type, creator_name)
                    if add_to_bulletin:
                        post_to_bulletin(committee, next_meeting_date, next_meeting_time,
                                         next_meeting_location, meeting_type, creator_name)

                st.session_state.ai_result = None
                st.session_state.n_agenda_items = 3
                st.success("✅ Minutes saved!")
                if next_meeting_date and (add_to_calendar or add_to_bulletin):
                    parts = []
                    if add_to_calendar: parts.append("Communal Calendar")
                    if add_to_bulletin: parts.append("Daily Bulletin")
                    st.info(f"📅 Next meeting ({fmt_date(next_meeting_date)}) added to: {' & '.join(parts)}")
                st.rerun()

def render_ai_assistant(committee, cfg):
    """AI transcript/notes → structured minutes."""
    st.markdown(f"""
    <div class="ai-box">
      <h4>🤖 AI Minutes Assistant</h4>
      <p style="font-size:0.85rem;color:#0c4a6e;margin:0;">
        Paste a meeting transcript or rough notes below and the AI will structure them
        into the DfE meeting format. You can review and edit before saving.
      </p>
    </div>
    """, unsafe_allow_html=True)

    mode = st.radio("Mode", ["📹 Structure from transcript", "✏️ Improve typed notes"],
                    horizontal=True, key="ai_mode")
    mode_key = "transcript" if "transcript" in mode else "improve"

    col1, col2 = st.columns([3,1])
    with col1:
        meeting_date_ai = st.date_input("Meeting date", value=today, key="ai_meeting_date")
    with col2:
        pass

    raw_text = st.text_area(
        "Paste transcript or rough notes here:",
        height=250,
        placeholder="e.g.\n\nMeeting opened at 3:30pm by Sarah.\nPresent: Sarah Jones, Tom Smith, Julie Brown.\nApologies from Candice.\n\nPrevious minutes moved by Tom, seconded by Julie. Carried.\n\nItem 1 - Budget Review...",
        key="ai_raw_text"
    )

    if st.button("🤖 Process with AI", type="primary", disabled=not raw_text.strip()):
        with st.spinner("AI is structuring your minutes... ⏳"):
            result = ai_structure_minutes(raw_text, committee, meeting_date_ai, mode_key)
            if result:
                st.session_state.ai_result = result
                st.session_state.n_agenda_items = max(len(result.get("agenda_items") or []), 3)
                st.success("✅ Done! Switch to the 'Record New Minutes' tab to review and save.")
                st.rerun()

    if st.session_state.get("ai_result"):
        st.markdown("---")
        st.markdown("**✅ AI result ready** — switch to the 📝 Record New Minutes tab to review and save it.")
        ai = st.session_state.ai_result
        with st.expander("👀 Preview AI output"):
            present = ai.get("attendance") or []
            if isinstance(present, str): present = [present]
            apologies = ai.get("apologies") or []
            if isinstance(apologies, str): apologies = [apologies]
            st.markdown(f"**Present:** {', '.join(present) if present else '—'}")
            st.markdown(f"**Apologies:** {', '.join(apologies) if apologies else '—'}")
            items = ai.get("agenda_items") or []
            if items:
                st.markdown(f"**{len(items)} agenda item(s) found:**")
                for i, item in enumerate(items,1):
                    if isinstance(item, dict):
                        st.markdown(f"- {i}. **{item.get('title','?')}** — {item.get('outcome','')}")
        if st.button("🗑 Clear AI result", key="clear_ai"):
            st.session_state.ai_result = None
            st.session_state.n_agenda_items = 3
            st.rerun()

# ─── SCHEDULE TAB ─────────────────────────────────────────────────────────────
def render_schedule_tab(committee):
    cfg = COMMITTEES[committee]
    upcoming = db_scheduled_meetings(committee)
    all_sched = db_all_scheduled(committee)
    past = [s for s in all_sched if str(s.get("meeting_date","")) < str(today)]
    members = db_get_members(committee)

    tab_sched, tab_members = st.tabs(["📅 Meetings", "👥 Members & Emails"])

    # ══════════════ MEETINGS ══════════════
    with tab_sched:
        # Next meeting display
        if upcoming:
            nm = upcoming[0]
            invite_tags = ""
            if nm.get("invites_sent"):
                invite_tags = f'&nbsp;·&nbsp;<span style="color:#7c3aed;">✉️ Invites sent</span>'
            st.markdown(f"""
            <div style="background:{cfg['bg']};border:2px solid {cfg['border']};
                        border-radius:14px;padding:1.5rem;margin-bottom:1.25rem;">
              <div style="font-size:0.75rem;font-weight:700;color:{cfg['color']};
                          text-transform:uppercase;letter-spacing:0.06em;">Next Scheduled Meeting</div>
              <div style="font-size:1.5rem;font-weight:800;color:{cfg['color']};margin-top:0.3rem;">
                📅 {fmt_date(nm.get('meeting_date'))}
              </div>
              <div style="font-size:0.88rem;color:#555;margin-top:0.25rem;">
                {f"⏰ {nm.get('meeting_time')}" if nm.get('meeting_time') else ""}
                {f" &nbsp;📍 {nm.get('location')}" if nm.get('location') else ""}
                {f" &nbsp;📋 {nm.get('meeting_type','Ordinary')}" if nm.get('meeting_type') else ""}
              </div>
              <div style="margin-top:0.5rem;font-size:0.78rem;color:#888;">
                {"✅ Added to calendar" if nm.get("added_to_calendar") else ""}
                {"&nbsp;·&nbsp;" if nm.get("added_to_calendar") and nm.get("added_to_bulletin") else ""}
                {"📋 Added to bulletin" if nm.get("added_to_bulletin") else ""}
                {invite_tags}
              </div>
            </div>
            """, unsafe_allow_html=True)

            if len(upcoming) > 1:
                with st.expander(f"📅 {len(upcoming)-1} more upcoming meeting(s)"):
                    for m in upcoming[1:]:
                        st.markdown(f"- **{fmt_date(m.get('meeting_date'))}**"
                                   + (f" at {m.get('meeting_time')}" if m.get('meeting_time') else "")
                                   + (f" — {m.get('location')}" if m.get('location') else ""))
        else:
            st.markdown("""
            <div style="background:#f8fafc;border:2px dashed #cbd5e1;border-radius:12px;
                        padding:1.5rem;text-align:center;margin-bottom:1.25rem;color:#64748b;">
              📅 No upcoming meetings scheduled — add one below.
            </div>
            """, unsafe_allow_html=True)

        # Schedule new meeting
        with st.expander("➕ Schedule a New Meeting", expanded=not upcoming):
            if not members:
                st.markdown("""
                <div style="background:#fef3c7;border:1px solid #fcd34d;border-radius:8px;
                            padding:0.6rem 0.9rem;font-size:0.84rem;color:#92400e;margin-bottom:0.75rem;">
                  💡 Add committee members in the <strong>Members & Emails</strong> tab to send invites when scheduling.
                </div>
                """, unsafe_allow_html=True)

            with st.form("schedule_meeting", clear_on_submit=True):
                sc1, sc2 = st.columns(2)
                with sc1:
                    s_date = st.date_input("Meeting date *", value=today + timedelta(weeks=4))
                    s_type = st.selectbox("Meeting type", ["Ordinary","Special","Extraordinary","Annual"])
                    s_time = st.text_input("Time", placeholder="e.g. 3:30 PM")
                with sc2:
                    s_loc  = st.text_input("Location", placeholder="e.g. Staff Room")
                    s_by   = st.text_input("Scheduled by *", placeholder="Your name")
                    s_email = st.text_input("Your email (for invite sender)", placeholder="you@schools.sa.edu.au")

                # Integration options
                st.markdown("**Add to:**")
                ic1, ic2, ic3 = st.columns(3)
                with ic1: add_cal = st.checkbox("📅 Communal Calendar", value=True)
                with ic2: add_bul = st.checkbox("📋 Daily Bulletin", value=True)
                with ic3: send_invites = st.checkbox("✉️ Email Invites", value=bool(members))

                # Member selection for invites
                if members and send_invites:
                    st.markdown("**Select recipients:**")
                    member_checks = {}
                    mcols = st.columns(min(len(members), 3))
                    for i, m in enumerate(members):
                        with mcols[i % len(mcols)]:
                            member_checks[m["id"]] = st.checkbox(
                                f"{m['name']} ({m['email']})",
                                value=True,
                                key=f"invite_{m['id']}"
                            )

                # Agenda preview for invite
                pending_items = db_agenda_items(committee)
                pending_items = [i for i in pending_items if i.get("status","pending") == "pending"]
                include_agenda = False
                if pending_items:
                    include_agenda = st.checkbox(
                        f"📋 Include {len(pending_items)} pending agenda item(s) in invite",
                        value=True
                    )

                if st.form_submit_button("📅 Schedule Meeting", type="primary", use_container_width=True):
                    if not s_by.strip():
                        st.warning("Please enter your name.")
                    else:
                        cal_ok = bul_ok = False
                        if add_cal:
                            cal_ok = post_to_calendar(committee, s_date, s_time, s_loc, s_type, s_by)
                        if add_bul:
                            bul_ok = post_to_bulletin(committee, s_date, s_time, s_loc, s_type, s_by)

                        # Send email invites
                        invite_count = 0
                        invite_errors = []
                        if send_invites and members:
                            selected = [m for m in members if member_checks.get(m["id"], False)]
                            if selected:
                                agenda_to_send = pending_items if include_agenda else None
                                with st.spinner(f"Sending invites to {len(selected)} recipient(s)..."):
                                    invite_count, invite_errors = send_meeting_invites(
                                        committee, s_date, s_time, s_loc, s_type,
                                        s_by, selected, agenda_to_send
                                    )

                        db_save_scheduled({
                            "committee": committee,
                            "meeting_date": str(s_date),
                            "meeting_time": s_time.strip(),
                            "location": s_loc.strip(),
                            "meeting_type": s_type,
                            "added_to_calendar": cal_ok,
                            "added_to_bulletin": bul_ok,
                            "invites_sent": invite_count,
                            "created_by": s_by.strip(),
                        })

                        st.success(f"✅ Meeting scheduled for {fmt_date(s_date)}!")
                        parts = []
                        if add_cal: parts.append("📅 Calendar")
                        if add_bul: parts.append("📋 Bulletin")
                        if invite_count: parts.append(f"✉️ {invite_count} invite(s) sent")
                        if parts: st.info(" · ".join(parts))
                        if invite_errors:
                            st.warning(f"⚠️ Failed to send to: {', '.join(invite_errors)}")
                        st.rerun()

        # Past meetings
        if past:
            with st.expander(f"📂 Past meetings ({len(past)})"):
                for m in past:
                    c1, c2 = st.columns([8,1])
                    with c1:
                        st.markdown(f"**{fmt_date(m.get('meeting_date'))}** — {m.get('meeting_type','Ordinary')}"
                                   + (f" at {m.get('meeting_time')}" if m.get('meeting_time') else "")
                                   + (f" · {m.get('location')}" if m.get('location') else "")
                                   + (f" · ✉️ {m.get('invites_sent',0)} invites" if m.get('invites_sent') else ""))
                    with c2:
                        if st.session_state.is_admin:
                            if st.button("🗑️", key=f"del_sched_{m['id']}"):
                                db_delete_scheduled(m["id"])
                                st.rerun()

    # ══════════════ MEMBERS & EMAILS ══════════════
    with tab_members:
        cfg = COMMITTEES[committee]
        all_staff   = db_get_all_staff()
        membership  = db_get_committee_membership(committee)
        members     = db_get_members(committee)

        st.markdown(f"""
        <div style="background:{cfg['bg']};border:1px solid {cfg['border']};border-radius:10px;
                    padding:0.9rem 1.1rem;margin-bottom:1rem;font-size:0.85rem;color:{cfg['color']};">
          Tick staff members below to add them to this committee.
          When scheduling a meeting you can select exactly who receives an invite —
          they'll get a branded email with an <strong>.ics calendar attachment</strong>.
        </div>
        """, unsafe_allow_html=True)

        if not all_staff:
            st.markdown('<div class="info-box">No staff found in the system. Staff are managed in the main behaviour app.</div>', unsafe_allow_html=True)
        else:
            ROLE_COLORS = {
                "Chair":        ("#1a2e44","#e8edf3"),
                "Deputy Chair": ("#1d4ed8","#dbeafe"),
                "Secretary":    ("#065f46","#d1fae5"),
                "Member":       ("#374151","#f3f4f6"),
                "Observer":     ("#6b7280","#f9fafb"),
            }
            ROLES = ["Member","Chair","Deputy Chair","Secretary","Observer"]

            # List all staff alphabetically (staff_list has no program column)
            for s in all_staff:
                sid    = s["id"]
                sname  = s["name"]
                semail = s.get("email", "")
                is_member = sid in membership
                cur_role  = membership.get(sid, "Member")
                rc, rb = ROLE_COLORS.get(cur_role, ROLE_COLORS["Member"])

                col_check, col_info, col_role, col_save = st.columns([0.5, 4, 2, 1])
                with col_check:
                    ticked = st.checkbox("", value=is_member,
                                         key=f"mem_tick_{committee}_{sid}",
                                         label_visibility="collapsed")
                with col_info:
                    badge = f'<span style="background:{rb};color:{rc};font-size:0.68rem;font-weight:700;padding:0.1rem 0.45rem;border-radius:20px;">{cur_role}</span> ' if is_member else ""
                    st.markdown(
                        f'<div style="padding:0.35rem 0;font-size:0.88rem;">'
                        f'{badge}<strong>{sname}</strong>'
                        f'<span style="color:#888;font-size:0.78rem;margin-left:0.5rem;">✉️ {semail}</span>'
                        f'</div>', unsafe_allow_html=True)
                with col_role:
                    if ticked:
                        new_role = st.selectbox("", ROLES,
                                                index=ROLES.index(cur_role) if cur_role in ROLES else 0,
                                                key=f"mem_role_{committee}_{sid}",
                                                label_visibility="collapsed")
                    else:
                        new_role = "Member"
                        st.empty()
                with col_save:
                    st.write("")
                    if ticked and not is_member:
                        if st.button("➕", key=f"mem_add_{committee}_{sid}", help=f"Add {sname}"):
                            db_set_committee_membership(committee, sid, new_role)
                            st.rerun()
                    elif ticked and is_member and new_role != cur_role:
                        if st.button("💾", key=f"mem_save_{committee}_{sid}", help="Save role"):
                            db_set_committee_membership(committee, sid, new_role)
                            st.rerun()
                    elif not ticked and is_member:
                        if st.button("✖", key=f"mem_rem_{committee}_{sid}", help=f"Remove {sname}"):
                            db_remove_committee_membership(committee, sid)
                            st.rerun()

            # Summary
            if members:
                st.markdown("---")
                names = ", ".join(m["name"] for m in members)
                st.markdown(f"**{len(members)} member{'s' if len(members)!=1 else ''} on this committee:** {names}")

        # Email config status
        st.markdown("---")
        smtp_conf = st.secrets.get("smtp", {})
        smtp_user = smtp_conf.get("user","")
        smtp_host = smtp_conf.get("host","smtp.gmail.com")
        if smtp_user:
            st.markdown(f"""
            <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;
                        padding:0.6rem 0.9rem;font-size:0.83rem;color:#15803d;">
              ✅ <strong>Email configured</strong> — sending via {smtp_user} ({smtp_host})
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#fef3c7;border:1px solid #fcd34d;border-radius:8px;
                        padding:0.6rem 0.9rem;font-size:0.83rem;color:#92400e;">
              ⚠️ <strong>Email not configured.</strong> Add this to your Streamlit secrets:<br><br>
              <code>[smtp]</code><br>
              <code>host = "smtp.gmail.com"</code><br>
              <code>port = 587</code><br>
              <code>user = "clc.digitalstaffmeeting@gmail.com"</code><br>
              <code>password = "your-16-char-app-password"</code><br>
              <code>from_name = "CLC Committees"</code>
            </div>
            """, unsafe_allow_html=True)

# ─── MAIN COMMITTEE VIEW ──────────────────────────────────────────────────────
def render_committee(committee):
    cfg = COMMITTEES[committee]

    # Header
    st.markdown(f"""
    <div class="comm-header" style="background:linear-gradient(135deg,{cfg['color']},{cfg['color']}cc);">
      <div style="font-size:3rem;">{cfg['emoji']}</div>
      <div>
        <h1>{committee} Committee</h1>
        <p>Cowandilla Learning Centre · {cfg['desc']}</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Top bar
    col1, col2, col3 = st.columns([5, 2, 1])
    with col2:
        if not st.session_state.is_admin:
            with st.expander("🔐 Admin"):
                adpw = st.text_input("Admin password", type="password", key="adpw")
                if st.button("Sign In", type="primary", use_container_width=True, key="admin_sign_in"):
                    if adpw == st.secrets.get(ADMIN_PASSWORD_KEY, ADMIN_DEFAULT_PW):
                        st.session_state.is_admin = True
                        st.rerun()
                    else:
                        st.error("Incorrect admin password.")
        else:
            st.success("🔓 Admin")
            if st.button("Sign Out", use_container_width=True):
                st.session_state.is_admin = False
                st.rerun()
    with col3:
        if st.button("← Back", use_container_width=True):
            st.session_state.selected_committee = None
            st.session_state.ai_result = None
            st.session_state.n_agenda_items = 3
            st.rerun()

    # Tabs
    tab_agenda, tab_minutes, tab_schedule = st.tabs([
        "📋 Agenda",
        "📝 Minutes",
        "📅 Schedule",
    ])

    with tab_agenda:
        render_agenda_tab(committee)

    with tab_minutes:
        render_minutes_tab(committee)

    with tab_schedule:
        render_schedule_tab(committee)

# ─── MAIN ROUTER ──────────────────────────────────────────────────────────────
# Read ?committee= query param from portal link — skip landing page if set
committee = st.session_state.selected_committee

if committee is None:
    landing_page()
elif not is_authed(committee):
    auth_gate(committee)
else:
    render_committee(committee)

# ─── FOOTER ──────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:2rem 0 0.5rem;color:#aaa;font-size:0.76rem;">
Cowandilla Learning Centre · Committee Management System
</div>
""", unsafe_allow_html=True)
