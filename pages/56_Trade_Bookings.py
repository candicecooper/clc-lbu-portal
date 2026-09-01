"""
56_Trade_Bookings.py
=====================
Tradesperson / contractor booking tool for the CLC-LBU staff portal.

WHAT THIS DOES
--------------
Staff can quickly log a tradesperson/contractor booking with full detail
(company, contact, phone, work type, time, access notes, etc). That full
detail is only ever shown inside THIS tool — the whole page requires
staff sign-in, since it holds contact/company detail.

The Calendar (12_Calendar.py) and Daily Bulletin show only a short,
generic, student-safe line built from the booking, e.g.:

    Maintenance - repairing wall
    IT Works - network cabling upgrade

12_Calendar.py already reads trade_bookings directly (db_trades() /
trade_events()) and 1_Daily_Bulletin.py already reads it via
load_todays_trade_bookings() — both select only the sanitized columns,
so no separate utils file or wiring is needed for this to show up there.

Table: trade_bookings — SQL to create it is in trade_bookings_schema.sql.
"""

from theme import apply_clc_theme
import streamlit as st
from supabase import create_client, Client
from datetime import date, datetime, time as dtime, timedelta
import pandas as pd
import os

st.set_page_config(page_title="Trade Bookings", page_icon="🔧", layout="wide", initial_sidebar_state="collapsed")
apply_clc_theme()

st.sidebar.markdown(
    '<a href="https://16cefb77.clc-portal.pages.dev/" target="_self" style="display:block;text-align:center;'
    'background:#1A7A7A;color:white;font-weight:600;font-size:0.85rem;'
    'padding:0.5rem;border-radius:8px;text-decoration:none;margin-bottom:0.75rem;">'
    '🏠 Back to Staff Portal</a>',
    unsafe_allow_html=True
)

# ── Staff sign-in (whole page requires sign-in — full detail here is sensitive) ──
def _tb_is_signed_in():
    return bool(st.session_state.get("_tb_staff_name", "").strip())

def _tb_staff_name():
    return st.session_state.get("_tb_staff_name", "").strip()

st.sidebar.markdown("---")
if _tb_is_signed_in():
    st.sidebar.success(f"✅ Signed in as **{_tb_staff_name()}**")
    if st.sidebar.button("🔓 Sign out", use_container_width=True):
        st.session_state["_tb_staff_name"] = ""
        st.rerun()
else:
    st.sidebar.markdown("### 🔐 Staff Sign In")
    st.sidebar.caption("Sign in to view or add trade/contractor bookings.")
    with st.sidebar.form("tb_signin_form", clear_on_submit=False):
        _sn_input = st.text_input("Your name", placeholder="e.g. Candice Cooper")
        _sn_pin   = st.text_input("Staff password", type="password", placeholder="Staff password")
        if st.form_submit_button("Sign In", use_container_width=True, type="primary"):
            try:    _correct = st.secrets.get("APP_PASSWORD", "")
            except: _correct = os.environ.get("APP_PASSWORD", "")
            if not _correct:
                _correct = "clcstaff2026"
            if not _sn_input.strip():
                st.sidebar.warning("Please enter your name.")
            elif _sn_pin != _correct:
                st.sidebar.error("Incorrect password. Please try again.")
            else:
                st.session_state["_tb_staff_name"] = _sn_input.strip()
                st.rerun()
st.sidebar.markdown("---")

@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
supabase = init_supabase()

TABLE_NAME = "trade_bookings"

WORK_TYPES = [
    "Electrical", "Plumbing", "Building/Carpentry", "Painting", "Glazing",
    "Locksmith", "HVAC/Air-con", "Fire Safety", "IT/Telecommunications",
    "Cleaning", "Grounds/Landscaping", "Pest Control", "Security/Alarm",
    "Other",
]

# Maps a specific work type to the generic category shown on Calendar/Bulletin
DISPLAY_CATEGORY_MAP = {
    "Electrical": "Maintenance",
    "Plumbing": "Maintenance",
    "Building/Carpentry": "Maintenance",
    "Painting": "Maintenance",
    "Glazing": "Maintenance",
    "Locksmith": "Maintenance",
    "HVAC/Air-con": "Maintenance",
    "Fire Safety": "Maintenance",
    "IT/Telecommunications": "IT Works",
    "Cleaning": "Cleaning",
    "Grounds/Landscaping": "Grounds",
    "Pest Control": "Pest Control",
    "Security/Alarm": "Security",
    "Other": "Onsite Works",
}

LOCATIONS = [
    "Whole site", "Front office/admin", "JP building", "PY building",
    "SY building", "Hall/gym", "Yard/grounds", "Carpark", "Other (see notes)",
]

STATUSES = ["Booked", "Confirmed", "Completed", "Cancelled"]

# South Australian public (state) school term dates, as published by the
# Department for Education (education.sa.gov.au/students/term-dates-south-australian-state-schools).
# SA DfE publishes these year by year — add the next year here once they're
# confirmed; term_view() will show a warning for any year not listed below.
SA_SCHOOL_TERMS = {
    2026: [
        (1, date(2026, 1, 27), date(2026, 4, 10)),
        (2, date(2026, 4, 27), date(2026, 7, 3)),
        (3, date(2026, 7, 20), date(2026, 9, 25)),
        (4, date(2026, 10, 12), date(2026, 12, 11)),
    ],
    2027: [
        (1, date(2027, 1, 27), date(2027, 4, 9)),
        (2, date(2027, 4, 26), date(2027, 7, 2)),
        (3, date(2027, 7, 19), date(2027, 9, 24)),
        (4, date(2027, 10, 11), date(2027, 12, 10)),
    ],
}

def get_sa_terms(year):
    return SA_SCHOOL_TERMS.get(year, [])


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------

def fetch_bookings(sb, start_date=None, end_date=None, status_filter=None):
    query = sb.table(TABLE_NAME).select("*")
    if start_date:
        query = query.gte("booking_date", start_date.isoformat())
    if end_date:
        query = query.lte("booking_date", end_date.isoformat())
    if status_filter and status_filter != "All":
        query = query.eq("status", status_filter)
    result = query.order("booking_date").order("start_time").execute()
    return result.data or []


def insert_booking(sb, record):
    return sb.table(TABLE_NAME).insert(record).execute()


def update_booking(sb, booking_id, record):
    return sb.table(TABLE_NAME).update(record).eq("id", booking_id).execute()


def delete_booking(sb, booking_id):
    return sb.table(TABLE_NAME).delete().eq("id", booking_id).execute()


def build_public_summary(work_type: str, work_summary: str) -> str:
    """The only string that should ever leave this tool for Calendar/Bulletin."""
    category = DISPLAY_CATEGORY_MAP.get(work_type, "Onsite Works")
    summary = (work_summary or "").strip()
    return f"{category} - {summary}" if summary else category


# ---------------------------------------------------------------------------
# UI: Add / Edit booking form
# ---------------------------------------------------------------------------

def booking_form(sb, existing=None):
    is_edit = existing is not None
    st.subheader("Edit booking" if is_edit else "New tradesperson / contractor booking")

    with st.form("trade_booking_form", clear_on_submit=not is_edit):
        col1, col2 = st.columns(2)
        with col1:
            booking_date = st.date_input(
                "Date",
                value=pd.to_datetime(existing["booking_date"]).date() if is_edit else date.today(),
            )
            start_time = st.time_input(
                "Expected start time",
                value=pd.to_datetime(existing["start_time"]).time() if is_edit and existing.get("start_time") else dtime(9, 0),
            )
            end_time = st.time_input(
                "Expected end time",
                value=pd.to_datetime(existing["end_time"]).time() if is_edit and existing.get("end_time") else dtime(12, 0),
            )
            work_type = st.selectbox(
                "Type of work",
                WORK_TYPES,
                index=WORK_TYPES.index(existing["work_type"]) if is_edit and existing.get("work_type") in WORK_TYPES else 0,
            )
            location_onsite = st.selectbox(
                "Location onsite",
                LOCATIONS,
                index=LOCATIONS.index(existing["location_onsite"]) if is_edit and existing.get("location_onsite") in LOCATIONS else 0,
            )
        with col2:
            company_name = st.text_input("Company", value=existing.get("company_name", "") if is_edit else "")
            contact_name = st.text_input("Contact name", value=existing.get("contact_name", "") if is_edit else "")
            contact_phone = st.text_input("Contact phone", value=existing.get("contact_phone", "") if is_edit else "")
            contact_email = st.text_input("Contact email (optional)", value=existing.get("contact_email", "") if is_edit else "")
            booked_by = st.text_input(
                "Booked by",
                value=existing.get("booked_by", "") if is_edit else _tb_staff_name(),
            )
            status = st.selectbox(
                "Status",
                STATUSES,
                index=STATUSES.index(existing["status"]) if is_edit and existing.get("status") in STATUSES else 0,
            )

        st.markdown("---")
        work_summary = st.text_input(
            "Short work summary (this is what will show publicly on the Calendar and Bulletin — keep it brief and generic)",
            value=existing.get("work_summary", "") if is_edit else "",
            placeholder="e.g. repairing wall, replacing air-con unit, cabling upgrade",
        )
        preview_category = DISPLAY_CATEGORY_MAP.get(work_type, "Onsite Works")
        st.caption(f"Public display preview: **{build_public_summary(work_type, work_summary) or preview_category}**")

        internal_notes = st.text_area(
            "Detailed / internal notes (never shown outside this tool)",
            value=existing.get("internal_notes", "") if is_edit else "",
            placeholder="Full job detail, quote/PO number, materials, follow-up needed, etc.",
        )
        access_requirements = st.text_area(
            "Access requirements (keys, alarm codes, parking, supervision needed)",
            value=existing.get("access_requirements", "") if is_edit else "",
        )

        col3, col4, col5 = st.columns(3)
        with col3:
            induction_completed = st.checkbox(
                "WHS/site induction completed",
                value=existing.get("induction_completed", False) if is_edit else False,
            )
        with col4:
            sign_in_required = st.checkbox(
                "Sign-in required on arrival",
                value=existing.get("sign_in_required", True) if is_edit else True,
            )
        with col5:
            students_nearby = st.checkbox(
                "Work area is near students",
                value=existing.get("students_nearby", False) if is_edit else False,
            )

        if students_nearby:
            st.warning(
                "Flagged as near students — consider scheduling outside student hours, "
                "or note supervision/exclusion arrangements in internal notes."
            )

        submitted = st.form_submit_button("Save booking")

        if submitted:
            if not company_name or not contact_name or not contact_phone or not work_summary:
                st.error("Company, contact name, contact phone, and a short work summary are all required.")
                return

            record = {
                "booking_date": booking_date.isoformat(),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "work_type": work_type,
                "display_category": DISPLAY_CATEGORY_MAP.get(work_type, "Onsite Works"),
                "work_summary": work_summary.strip(),
                "internal_notes": internal_notes.strip(),
                "company_name": company_name.strip(),
                "contact_name": contact_name.strip(),
                "contact_phone": contact_phone.strip(),
                "contact_email": contact_email.strip(),
                "location_onsite": location_onsite,
                "access_requirements": access_requirements.strip(),
                "induction_completed": induction_completed,
                "sign_in_required": sign_in_required,
                "students_nearby": students_nearby,
                "booked_by": booked_by,
                "status": status,
            }

            if is_edit:
                update_booking(sb, existing["id"], record)
                st.success("Booking updated.")
            else:
                insert_booking(sb, record)
                st.success("Booking added.")
            st.rerun()


# ---------------------------------------------------------------------------
# UI: List view (full detail — this tool only)
# ---------------------------------------------------------------------------

def list_view(sb):
    st.subheader("Upcoming & recent bookings")

    colf1, colf2, colf3 = st.columns(3)
    with colf1:
        range_choice = st.selectbox("Show", ["Next 14 days", "This term (custom range)", "All"])
    with colf2:
        status_filter = st.selectbox("Status", ["All"] + STATUSES)
    with colf3:
        search = st.text_input("Search company/contact/work", "")

    start_date, end_date = None, None
    if range_choice == "Next 14 days":
        start_date = date.today()
        end_date = pd.Timestamp(date.today()) + pd.Timedelta(days=14)
        end_date = end_date.date()
    elif range_choice == "This term (custom range)":
        c1, c2 = st.columns(2)
        with c1:
            start_date = st.date_input("From", value=date.today())
        with c2:
            end_date = st.date_input("To", value=(pd.Timestamp(date.today()) + pd.Timedelta(days=30)).date())

    bookings = fetch_bookings(sb, start_date, end_date, status_filter)

    if search:
        s = search.lower()
        bookings = [
            b for b in bookings
            if s in (b.get("company_name") or "").lower()
            or s in (b.get("contact_name") or "").lower()
            or s in (b.get("work_summary") or "").lower()
        ]

    if not bookings:
        st.info("No bookings found for this range.")
        return

    for b in bookings:
        header = f"{b['booking_date']} — {build_public_summary(b['work_type'], b['work_summary'])} — {b.get('company_name','')}"
        with st.expander(header):
            st.write(f"**Status:** {b.get('status','')}")
            st.write(f"**Time:** {b.get('start_time','')} – {b.get('end_time','')}")
            st.write(f"**Location:** {b.get('location_onsite','')}")
            st.write(f"**Company:** {b.get('company_name','')}")
            st.write(f"**Contact:** {b.get('contact_name','')} — {b.get('contact_phone','')}"
                     + (f" — {b.get('contact_email')}" if b.get('contact_email') else ""))
            st.write(f"**Booked by:** {b.get('booked_by','')}")
            if b.get("students_nearby"):
                st.warning("Near students")
            st.write(f"**WHS induction completed:** {'Yes' if b.get('induction_completed') else 'No'}")
            st.write(f"**Sign-in required:** {'Yes' if b.get('sign_in_required') else 'No'}")
            if b.get("access_requirements"):
                st.write(f"**Access notes:** {b['access_requirements']}")
            if b.get("internal_notes"):
                st.write(f"**Internal notes:** {b['internal_notes']}")

            colA, colB = st.columns(2)
            with colA:
                if st.button("Edit", key=f"edit_{b['id']}"):
                    st.session_state["editing_booking"] = b
                    st.rerun()
            with colB:
                if st.button("Delete", key=f"delete_{b['id']}"):
                    delete_booking(sb, b["id"])
                    st.success("Deleted.")
                    st.rerun()


# ---------------------------------------------------------------------------
# UI: Term view — trade bookings across a whole SA school term
# ---------------------------------------------------------------------------

def term_view(sb):
    st.subheader("Term view")
    st.caption("Bookings across a whole SA school term, week by week — full detail visible here since this is staff-only.")

    available_years = sorted(SA_SCHOOL_TERMS.keys())
    today_d = date.today()
    default_year = today_d.year if today_d.year in available_years else available_years[0]

    colY, colT = st.columns(2)
    with colY:
        year = st.selectbox("Year", available_years, index=available_years.index(default_year))

    terms = get_sa_terms(year)
    if not terms:
        st.warning(
            f"Term dates for {year} haven't been added yet. SA DfE publishes these year by year — "
            f"add them to SA_SCHOOL_TERMS near the top of this file once confirmed at "
            f"education.sa.gov.au/students/term-dates-south-australian-state-schools."
        )
        return

    # Default to whichever term contains today, else Term 1
    default_term_idx = 0
    for i, (_, ts, te) in enumerate(terms):
        if ts <= today_d <= te:
            default_term_idx = i
            break

    term_labels = [f"Term {t[0]} ({t[1].strftime('%-d %b')} \u2013 {t[2].strftime('%-d %b')})" for t in terms]
    with colT:
        term_idx = st.selectbox("Term", range(len(terms)), format_func=lambda i: term_labels[i], index=default_term_idx)

    term_no, t_start, t_end = terms[term_idx]
    st.markdown(f"**Term {term_no}, {year}** \u2014 {t_start.strftime('%A %-d %B')} to {t_end.strftime('%A %-d %B')}")

    bookings = fetch_bookings(sb, t_start, t_end)
    by_date = {}
    for b in bookings:
        by_date.setdefault(b["booking_date"], []).append(b)

    if not bookings:
        st.info("No trade bookings recorded for this term yet.")

    # Walk week by week (Mon-Fri) across the term
    cur = t_start - timedelta(days=t_start.weekday())  # back up to the Monday of week 1
    week_num = 1
    while cur <= t_end:
        week_dates = [cur + timedelta(days=i) for i in range(5)]
        if any(t_start <= d <= t_end for d in week_dates):
            st.markdown(f"###### Week {week_num}")
            cols = st.columns(5)
            for i, d in enumerate(week_dates):
                in_term = t_start <= d <= t_end
                with cols[i]:
                    is_today = d == today_d
                    header_bg = "#1A7A7A" if is_today else ("#f3f4f6" if in_term else "#fafafa")
                    header_fg = "white" if is_today else ("#374151" if in_term else "#d1d5db")
                    st.markdown(
                        f'<div style="padding:.3rem .4rem;border-radius:6px 6px 0 0;'
                        f'font-size:.72rem;font-weight:700;background:{header_bg};color:{header_fg};">'
                        f'{d.strftime("%a %-d %b")}</div>',
                        unsafe_allow_html=True,
                    )
                    if not in_term:
                        st.markdown('<div style="padding:.4rem;"></div>', unsafe_allow_html=True)
                        continue
                    day_bookings = sorted(by_date.get(d.isoformat(), []), key=lambda x: str(x.get("start_time") or ""))
                    if not day_bookings:
                        st.markdown('<div style="padding:.35rem;color:#d1d5db;font-size:.7rem;border:1px solid #f0f0f0;border-top:none;border-radius:0 0 6px 6px;">\u2014</div>', unsafe_allow_html=True)
                        continue
                    chips = ""
                    for b in day_bookings:
                        label = build_public_summary(b.get("work_type",""), b.get("work_summary",""))
                        t_str = (b.get("start_time") or "")[:5]
                        status = b.get("status","")
                        status_dot = {"Booked":"#e8a125","Confirmed":"#4a8f33","Completed":"#9ca3af","Cancelled":"#c0392b"}.get(status, "#9ca3af")
                        chips += (
                            f'<div style="background:#eef6f6;border-left:3px solid {status_dot};padding:.25rem .4rem;'
                            f'margin-top:.25rem;border-radius:4px;font-size:.68rem;line-height:1.25;">'
                            f'<strong>{t_str}</strong> {label}<br>'
                            f'<span style="color:#888;">{b.get("company_name","")}</span></div>'
                        )
                    st.markdown(
                        f'<div style="border:1px solid #f0f0f0;border-top:none;border-radius:0 0 6px 6px;padding:.15rem .3rem .35rem;">{chips}</div>',
                        unsafe_allow_html=True,
                    )
        cur += timedelta(days=7)
        week_num += 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.title("🔧 Trade & Contractor Bookings")

    if not _tb_is_signed_in():
        st.info("🔐 **Sign in via the sidebar** to view or add trade/contractor bookings. Full contact detail here is staff-only.", icon="ℹ️")
        return

    st.caption(
        "Full detail here is staff-only. The Calendar and Daily Bulletin will only ever "
        "show a short generic line (e.g. \"Maintenance - repairing wall\")."
    )

    sb = supabase

    if "editing_booking" in st.session_state:
        booking_form(sb, existing=st.session_state["editing_booking"])
        if st.button("Cancel edit"):
            del st.session_state["editing_booking"]
            st.rerun()
        st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📋 View bookings", "➕ Add booking", "🗓️ Term view"])
    with tab1:
        list_view(sb)
    with tab2:
        booking_form(sb)
    with tab3:
        term_view(sb)


main()


# ---------------------------------------------------------------------------
# DEPLOYMENT CHECKLIST
# ---------------------------------------------------------------------------
#
# 1) Run trade_bookings_schema.sql once in the SQL editor of the same
#    Supabase project your other tables (clc_events, pac_meetings, etc.)
#    already live in.
#
# 2) Push this file as 56_Trade_Bookings.py into your Streamlit pages
#    folder in the clc-lbu-portal repo, alongside 12_Calendar.py, and
#    let Render redeploy. It reads SUPABASE_URL / SUPABASE_KEY / APP_PASSWORD
#    from st.secrets exactly the way 12_Calendar.py does, so no new secrets
#    are needed if Calendar already works.
#
# 3) 12_Calendar.py (db_trades()/trade_events()) and 1_Daily_Bulletin.py
#    (load_todays_trade_bookings()) already read this table directly and
#    display only the sanitized columns — no separate utils file needed.
#
# 4) The Cloudflare tile launcher already links to
#    https://clc-lbu-portal.onrender.com/Trade_Bookings — that slug is
#    derived from the filename with the leading number stripped, so it
#    stays correct regardless of whether this file is numbered 55, 56, etc.
