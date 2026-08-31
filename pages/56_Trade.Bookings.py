"""
56_Trade_Bookings.py
=====================
Tradesperson / contractor booking tool for the CLC-LBU staff portal.

WHAT THIS DOES
--------------
Staff can quickly log a tradesperson/contractor booking with full detail
(company, contact, phone, work type, time, access notes, etc). That full
detail is only ever shown inside THIS tool.

The Calendar (12_Calendar.py) and Staff Bulletin (11_Staff_Bulletin.py) show
only a short, generic, student-safe line built from the booking, e.g.:

    Maintenance - repairing wall
    IT Works - network cabling upgrade

To pull that generic line into another page, import and call:

    from trade_bookings_utils import get_public_bookings_for_date

See the bottom of this file ("INTEGRATION NOTES") for exactly how to wire
that into your existing Calendar and Bulletin pages.

ASSUMPTIONS TO CONFIRM / ADJUST
--------------------------------
1. Auth: this uses `staff_auth.require_staff_login()` as a stand-in for
   whatever your shared staff_auth.py actually exposes. Swap the import/
   call at the top of main() to match the real function name you use
   elsewhere (e.g. in 43_communication_log.py).
2. Supabase connection: uses `get_supabase_client()` from a small shared
   helper (supabase_client.py) — adjust to match however your other pages
   currently create their Supabase client (env var names etc).
3. Table name: `trade_bookings`. SQL to create it is below.
4. Staff name list: swap the placeholder STAFF_NAMES list for however you
   already pull staff names elsewhere (e.g. from a Supabase staff table).
"""

import streamlit as st
from datetime import date, datetime, time as dtime
import pandas as pd

# ---- adjust these two imports to match your existing modules ----
try:
    from staff_auth import require_staff_login
except ImportError:
    def require_staff_login():
        # placeholder — replace with your real staff_auth call
        return True

try:
    from supabase_client import get_supabase_client
except ImportError:
    from supabase import create_client
    import os

    def get_supabase_client():
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        return create_client(url, key)

TABLE_NAME = "trade_bookings"

# Replace with however staff names are already sourced elsewhere in the portal
STAFF_NAMES = [
    "Candice Cooper", "Susan Furga", "Annette Balestrin", "Ben Selga",
    "Ben Sutton", "Brenton", "Caitie", "Cheryl", "Jacqui", "Naomi", "Vinnie",
    "Other / not listed",
]

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
            booked_by = st.selectbox(
                "Booked by",
                STAFF_NAMES,
                index=STAFF_NAMES.index(existing["booked_by"]) if is_edit and existing.get("booked_by") in STAFF_NAMES else 0,
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
# Main
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="Trade Bookings", layout="wide")
    require_staff_login()

    st.title("🔧 Trade & Contractor Bookings")
    st.caption(
        "Full detail here is staff-only. The Calendar and Daily Bulletin will only ever "
        "show a short generic line (e.g. \"Maintenance - repairing wall\")."
    )

    sb = get_supabase_client()

    if "editing_booking" in st.session_state:
        booking_form(sb, existing=st.session_state["editing_booking"])
        if st.button("Cancel edit"):
            del st.session_state["editing_booking"]
            st.rerun()
        st.markdown("---")

    tab1, tab2 = st.tabs(["📋 View bookings", "➕ Add booking"])
    with tab1:
        list_view(sb)
    with tab2:
        booking_form(sb)


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# INTEGRATION NOTES (read this)
# ---------------------------------------------------------------------------
#
# 1) Create the Supabase table (run once in the SQL editor of whichever
#    Supabase project you want this to live in):
#
#    create table trade_bookings (
#        id bigint generated always as identity primary key,
#        booking_date date not null,
#        start_time time,
#        end_time time,
#        work_type text,
#        display_category text,
#        work_summary text,
#        internal_notes text,
#        company_name text,
#        contact_name text,
#        contact_phone text,
#        contact_email text,
#        location_onsite text,
#        access_requirements text,
#        induction_completed boolean default false,
#        sign_in_required boolean default true,
#        students_nearby boolean default false,
#        booked_by text,
#        status text default 'Booked',
#        created_at timestamptz default now()
#    );
#    -- add RLS policies to match how your other tables (e.g. communication log) are set up.
#
# 2) Create trade_bookings_utils.py in the repo root (or wherever your shared
#    helpers live) with this function, so Calendar and Bulletin only ever see
#    the sanitised line — never the company/contact/phone fields:
#
#    from supabase_client import get_supabase_client
#
#    def get_public_bookings_for_date(target_date):
#        sb = get_supabase_client()
#        result = (
#            sb.table("trade_bookings")
#            .select("booking_date,start_time,end_time,display_category,work_summary,status")
#            .eq("booking_date", target_date.isoformat())
#            .neq("status", "Cancelled")
#            .execute()
#        )
#        entries = []
#        for row in result.data or []:
#            label = f"{row['display_category']} - {row['work_summary']}"
#            entries.append({
#                "label": label,
#                "start_time": row.get("start_time"),
#                "end_time": row.get("end_time"),
#            })
#        return entries
#
# 3) In 12_Calendar.py, wherever you build the list of events/items for a
#    given day, add:
#
#    from trade_bookings_utils import get_public_bookings_for_date
#    trade_entries = get_public_bookings_for_date(the_day)
#    for t in trade_entries:
#        day_events.append(f"{t['start_time']}–{t['end_time']}: {t['label']}")
#
# 4) In 11_Staff_Bulletin.py, do the same in whatever section lists the day's
#    or week's onsite activity — pull get_public_bookings_for_date() for the
#    relevant date(s) and append the `label` string alongside other bulletin
#    items. No company/contact/phone fields are available to that page at all
#    since the select() above never requests them.
#
# 5) Swap the staff_auth / supabase_client placeholder imports at the top of
#    this file for your real modules, and swap STAFF_NAMES for however staff
#    names are already sourced elsewhere in the portal.
