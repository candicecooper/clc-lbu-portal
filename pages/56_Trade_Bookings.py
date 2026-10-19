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
import html

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

# Ventia service requests: lodged first (work order number + priority), then
# the contractor booking is added later once Ventia says who has been allocated.
# An "open" request has no booking date yet, so it never shows on the Calendar
# or Daily Bulletin until it has been booked.
PRIORITIES = ["P1", "P2", "P3", "P4"]
PRIORITY_COLOURS = {"P1": "#c0392b", "P2": "#e8731a", "P3": "#e8a125", "P4": "#6b7280"}
REQUEST_STATUSES = ["Requested", "Allocated"]   # Requested = waiting on Ventia; Allocated = contractor known, not yet booked

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
    rows = result.data or []
    # Open Ventia requests have no booking date yet — they live in the
    # "Ventia requests" tab, not in the dated bookings list or term view.
    return [r for r in rows if r.get("booking_date")]


def _is_ventia(r):
    return bool((r.get("ventia_wo_number") or "").strip())


def fetch_requests(sb):
    """Open Ventia jobs — lodged with Ventia and not yet completed or cancelled.
    That includes jobs that are booked with a contractor: they stay here until
    someone confirms the work is done. Most urgent first."""
    result = (sb.table(TABLE_NAME).select("*")
              .neq("status", "Completed").neq("status", "Cancelled").execute())
    rows = [r for r in (result.data or []) if _is_ventia(r)]
    return sorted(rows, key=lambda r: (r.get("priority") or "P9", str(r.get("requested_date") or ""), r.get("id") or 0))


def fetch_completed_requests(sb):
    """Ventia jobs that have been confirmed complete, newest first."""
    result = sb.table(TABLE_NAME).select("*").eq("status", "Completed").execute()
    rows = [r for r in (result.data or []) if _is_ventia(r)]
    return sorted(rows, key=lambda r: str(r.get("booking_date") or ""), reverse=True)


def set_status(sb, row, new_status, message):
    """Change a job's status, report the outcome after the rerun."""
    try:
        update_booking(sb, row["id"], {"status": new_status})
    except Exception as _e:
        st.error(f"⚠️ Couldn't update this job — nothing was changed: {explain_db_error(_e)}")
    else:
        flash(message)
        st.rerun()


def wo_matches(sb, wo_number, exclude_id=None):
    """Existing, non-cancelled rows already using this Ventia work order number."""
    rows = sb.table(TABLE_NAME).select("id,status").eq("ventia_wo_number", wo_number).execute().data or []
    return [r for r in rows if r.get("id") != exclude_id and r.get("status") != "Cancelled"]


def explain_db_error(err):
    msg = str(err)
    if any(k in msg for k in ("ventia_wo_number", "priority", "requested_date", "requested_by")) \
            or "booking_date" in msg or "23502" in msg:
        return (msg + "  —  this looks like the Ventia upgrade SQL hasn't been run yet. "
                "Run trade_bookings_ventia_upgrade.sql in the Supabase SQL editor, then try again.")
    return msg


def flash(message, kind="success"):
    """Show a message after the next rerun (a plain st.success followed by st.rerun() vanishes instantly)."""
    st.session_state["_tb_flash"] = (kind, message)


def insert_booking(sb, record):
    result = sb.table(TABLE_NAME).insert(record).execute()
    if not getattr(result, "data", None):
        raise RuntimeError("Supabase insert returned no data — the write may not have gone through.")
    return result


def update_booking(sb, booking_id, record):
    result = sb.table(TABLE_NAME).update(record).eq("id", booking_id).execute()
    if not getattr(result, "data", None):
        raise RuntimeError("Supabase update returned no data — the change may not have been saved.")
    return result


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
    # A request already lodged with Ventia, with no contractor booked yet
    from_request = is_edit and existing.get("status") in REQUEST_STATUSES
    if from_request:
        st.subheader(f"Book contractor — Ventia WO {existing.get('ventia_wo_number') or ''}")
        st.caption(
            f"{existing.get('priority') or ''} · {existing.get('work_type') or ''}. "
            "Add the contractor and the date/time now that Ventia has allocated the job."
        )
    else:
        st.subheader("Edit booking" if is_edit else "New tradesperson / contractor booking")

    # Unique key per form — two forms sharing one key raises a Streamlit error
    form_key = f"trade_booking_form_{existing['id']}" if is_edit else "trade_booking_form_new"
    with st.form(form_key, clear_on_submit=not is_edit):
        col1, col2 = st.columns(2)
        with col1:
            booking_date = st.date_input(
                "Date",
                value=pd.to_datetime(existing["booking_date"]).date() if is_edit and existing.get("booking_date") else date.today(),
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
            contact_phone = st.text_input("Contact phone (optional)", value=existing.get("contact_phone", "") if is_edit else "")
            contact_email = st.text_input("Contact email (optional)", value=existing.get("contact_email", "") if is_edit else "")
            booked_by = st.text_input(
                "Booked by",
                value=(existing.get("booked_by") or _tb_staff_name()) if is_edit else _tb_staff_name(),
            )
            default_status = existing.get("status") if is_edit and existing.get("status") in STATUSES else "Booked"
            status = st.selectbox("Status", STATUSES, index=STATUSES.index(default_status))

        colv1, colv2 = st.columns(2)
        with colv1:
            ventia_wo_number = st.text_input(
                "Ventia work order no. (optional)",
                value=(existing.get("ventia_wo_number") or "") if is_edit else "",
            )
        with colv2:
            _prio_opts = [""] + PRIORITIES
            _cur_prio = (existing.get("priority") or "") if is_edit else ""
            priority = st.selectbox(
                "Ventia priority (optional)", _prio_opts,
                index=_prio_opts.index(_cur_prio) if _cur_prio in _prio_opts else 0,
                format_func=lambda p: p or "Not set",
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
            if not company_name or not contact_name or not work_summary:
                st.error("Company, contact name, and a short work summary are all required.")
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
            # Only send the Ventia columns when there is something to record (or
            # something to clear), so plain bookings keep working either way.
            for _key, _val in (("ventia_wo_number", ventia_wo_number.strip()), ("priority", priority)):
                if _val or (is_edit and existing.get(_key)):
                    record[_key] = _val or None

            try:
                if is_edit:
                    update_booking(sb, existing["id"], record)
                else:
                    insert_booking(sb, record)
            except Exception as _save_err:
                st.error(f"⚠️ Couldn't save this booking — nothing was recorded: {explain_db_error(_save_err)}")
                return

            saved_label = build_public_summary(work_type, work_summary)
            flash(f"✅ Saved: {booking_date.strftime('%A %-d %B')} — {saved_label} ({company_name})")
            st.session_state.pop("editing_booking", None)
            st.rerun()


# ---------------------------------------------------------------------------
# UI: Ventia service requests — lodge first, book the contractor later
# ---------------------------------------------------------------------------

def request_form(sb, existing=None):
    is_edit = existing is not None
    st.subheader("Edit Ventia request" if is_edit else "Lodge a Ventia service request")
    st.caption(
        "Record the work order number and priority when you lodge the job with Ventia. "
        "The contractor and booking details are added later, once Ventia tells you who has been allocated."
    )

    form_key = f"ventia_request_form_{existing['id']}" if is_edit else "ventia_request_form_new"
    with st.form(form_key, clear_on_submit=not is_edit):
        c1, c2 = st.columns(2)
        with c1:
            wo_number = st.text_input(
                "Ventia work order number",
                value=(existing.get("ventia_wo_number") or "") if is_edit else "",
            )
            _prio_opts = [""] + PRIORITIES
            _cur_prio = (existing.get("priority") or "") if is_edit else ""
            priority = st.selectbox(
                "Priority", _prio_opts,
                index=_prio_opts.index(_cur_prio) if _cur_prio in _prio_opts else 0,
                format_func=lambda p: p or "Select priority…",
            )
            work_type = st.selectbox(
                "Type of service required", WORK_TYPES,
                index=WORK_TYPES.index(existing["work_type"]) if is_edit and existing.get("work_type") in WORK_TYPES else 0,
            )
        with c2:
            requested_date = st.date_input(
                "Date lodged",
                value=pd.to_datetime(existing["requested_date"]).date() if is_edit and existing.get("requested_date") else date.today(),
            )
            requested_by = st.text_input(
                "Lodged by",
                value=(existing.get("requested_by") or _tb_staff_name()) if is_edit else _tb_staff_name(),
            )
            location_onsite = st.selectbox(
                "Location onsite", LOCATIONS,
                index=LOCATIONS.index(existing["location_onsite"]) if is_edit and existing.get("location_onsite") in LOCATIONS else 0,
            )

        work_summary = st.text_input(
            "Short work summary (becomes the generic Calendar/Bulletin line once a contractor is booked — keep it brief)",
            value=(existing.get("work_summary") or "") if is_edit else "",
            placeholder="e.g. repairing wall, blocked drain, replacing air-con unit",
        )
        st.caption(f"Public display preview: **{build_public_summary(work_type, work_summary)}**")
        internal_notes = st.text_area(
            "Notes on the fault / job (staff only — never shown on Calendar or Bulletin)",
            value=(existing.get("internal_notes") or "") if is_edit else "",
        )

        submitted = st.form_submit_button("Save request")
        if submitted:
            if not wo_number.strip() or not priority:
                st.error("A Ventia work order number and a priority (P1–P4) are both required.")
                return

            record = {
                "ventia_wo_number": wo_number.strip(),
                "priority": priority,
                "work_type": work_type,
                "display_category": DISPLAY_CATEGORY_MAP.get(work_type, "Onsite Works"),
                "work_summary": work_summary.strip(),
                "internal_notes": internal_notes.strip(),
                "location_onsite": location_onsite,
                "requested_date": requested_date.isoformat(),
                "requested_by": requested_by.strip(),
            }
            try:
                if wo_matches(sb, wo_number.strip(), exclude_id=existing["id"] if is_edit else None):
                    st.error(f"Work order {wo_number.strip()} is already recorded in this tool — "
                             "find it in the Ventia requests list or the bookings list instead of entering it twice.")
                    return
                if is_edit:
                    update_booking(sb, existing["id"], record)
                else:
                    record.update({
                        "booking_date": None, "status": "Requested",
                        # blank strings (not NULL) so the booking form and lists never show "None"
                        "company_name": "", "contact_name": "", "contact_phone": "", "contact_email": "",
                        "access_requirements": "", "booked_by": "",
                    })
                    insert_booking(sb, record)
            except Exception as _save_err:
                st.error(f"⚠️ Couldn't save this request — nothing was recorded: {explain_db_error(_save_err)}")
                return

            flash(f"✅ Request saved: WO {wo_number.strip()} ({priority}) — {build_public_summary(work_type, work_summary)}. "
                  "It will stay in the open list until you book a contractor.")
            st.session_state.pop("editing_request", None)
            st.rerun()


def _booking_when(r):
    """'Tue 21 Oct, 09:00–12:00' for a dated booking, else ''."""
    if not r.get("booking_date"):
        return ""
    try:
        d = pd.to_datetime(r["booking_date"]).date()
    except Exception:
        return str(r["booking_date"])
    out = d.strftime("%a %-d %b")
    st_t, en_t = (r.get("start_time") or "")[:5], (r.get("end_time") or "")[:5]
    if st_t:
        out += f", {st_t}" + (f"–{en_t}" if en_t else "")
    return out


def request_stage(r, today_d):
    """(label, overdue) for where an open Ventia job is up to."""
    status = r.get("status")
    if status == "Requested":
        return "Awaiting allocation", False
    if status == "Allocated":
        return "Allocated — needs booking", False
    label = "Confirmed" if status == "Confirmed" else "Booked"
    when = _booking_when(r)
    overdue = False
    try:
        overdue = bool(r.get("booking_date")) and pd.to_datetime(r["booking_date"]).date() < today_d
    except Exception:
        pass
    text = f"{label} {when}".strip()
    if overdue:
        text += " — date has passed, confirm if done"
    return text, overdue


def requests_view(sb, open_requests, load_error=None):
    st.subheader("Open Ventia jobs")
    st.caption(
        "Every Ventia job that isn't finished yet, most urgent first. A job stays here from the moment you lodge it, "
        "through allocation and booking, until you click **Mark job completed** once the work has been done. "
        "Completed jobs move to the list below but still show in the Term view. "
        "Jobs only appear on the Calendar and Daily Bulletin once they have a booking date."
    )
    if load_error:
        st.error(f"⚠️ Couldn't load Ventia jobs: {load_error}")
        return
    if not open_requests:
        st.info("No open Ventia jobs. Lodge one above and it will stay here until the work is completed.")
        return

    today_d = date.today()
    for r in open_requests:
        rid = r["id"]
        wo = r.get("ventia_wo_number") or "no WO no."
        prio = r.get("priority") or "—"
        stage, overdue = request_stage(r, today_d)
        dated = bool(r.get("booking_date"))
        title = f"{'⏰ ' if overdue else ''}{prio} · WO {wo} · {r.get('work_type') or ''}"
        if r.get("work_summary"):
            title += f" — {r['work_summary']}"
        title += f"  [{stage}]"

        with st.expander(title):
            colour = PRIORITY_COLOURS.get(prio, "#6b7280")
            st.markdown(
                f'<span style="background:{colour};color:white;padding:.15rem .6rem;border-radius:10px;'
                f'font-weight:700;font-size:.85rem;">{html.escape(prio)}</span> '
                f'<span style="font-weight:600;">{html.escape(stage)}</span>',
                unsafe_allow_html=True,
            )
            if r.get("requested_date"):
                try:
                    lodged = pd.to_datetime(r["requested_date"]).date()
                    waited = (today_d - lodged).days
                    st.write(f"**Lodged:** {lodged.strftime('%a %-d %b %Y')} ({waited} day{'s' if waited != 1 else ''} ago)"
                             + (f" by {r['requested_by']}" if r.get("requested_by") else ""))
                except Exception:
                    pass
            st.write(f"**Service required:** {r.get('work_type') or ''}")
            st.write(f"**Location:** {r.get('location_onsite') or ''}")
            if dated:
                st.write(f"**Booked for:** {_booking_when(r)}")
            if r.get("company_name"):
                contact = r.get("contact_name") or ""
                if r.get("contact_phone"):
                    contact += f" — {r['contact_phone']}" if contact else r["contact_phone"]
                st.write(f"**Contractor:** {r['company_name']}" + (f" ({contact})" if contact else ""))
            if r.get("internal_notes"):
                st.write(f"**Notes:** {r['internal_notes']}")

            if r.get("status") == "Requested":
                alloc_co = st.text_input("Contractor allocated by Ventia (optional)", key=f"alloc_co_{rid}",
                                         placeholder="Fill in if Ventia has told you who it is")
                if st.button("✅ Ventia has allocated a contractor", key=f"alloc_{rid}"):
                    changes = {"status": "Allocated"}
                    if alloc_co.strip():
                        changes["company_name"] = alloc_co.strip()
                    try:
                        update_booking(sb, rid, changes)
                    except Exception as _e:
                        st.error(f"⚠️ Couldn't update this request: {explain_db_error(_e)}")
                    else:
                        flash(f"WO {wo} marked as allocated — book the contractor when you've agreed a time.")
                        st.rerun()

            if dated:
                # Booked with a contractor: the next step is confirming the work was done
                if st.button("✅ Mark job completed", key=f"done_{rid}", type="primary"):
                    set_status(sb, r, "Completed",
                               f"✅ WO {wo} marked completed. It has left the open list and still shows in the Term view.")
            else:
                st.caption("Not booked yet. If the work has already been done (or Ventia dealt with it directly), "
                           "you can mark it completed here — pick the date it was done so it shows in the Term view.")
                done_date = st.date_input("Date the work was done", value=today_d, key=f"donedate_{rid}")
                if st.button("✅ Mark job completed", key=f"donenow_{rid}", type="primary"):
                    try:
                        update_booking(sb, rid, {"status": "Completed", "booking_date": done_date.isoformat()})
                    except Exception as _e:
                        st.error(f"⚠️ Couldn't update this job — nothing was changed: {explain_db_error(_e)}")
                    else:
                        flash(f"✅ WO {wo} marked completed on {done_date.strftime('%a %-d %b')}. "
                              "It has left the open list and shows in the Term view.")
                        st.rerun()

            ca, cb, cc = st.columns(3)
            with ca:
                if dated:
                    if st.button("📅 Edit booking", key=f"editbk_{rid}"):
                        st.session_state.pop("editing_request", None)
                        st.session_state["editing_booking"] = r
                        st.rerun()
                else:
                    if st.button("📅 Book contractor", key=f"book_{rid}", type="primary"):
                        st.session_state.pop("editing_request", None)
                        st.session_state["editing_booking"] = r
                        st.rerun()
            with cb:
                if st.button("✏️ Edit request", key=f"editreq_{rid}"):
                    st.session_state.pop("editing_booking", None)
                    st.session_state["editing_request"] = r
                    st.rerun()
            with cc:
                sure = st.checkbox("Tick to confirm cancelling", key=f"cancel_ok_{rid}")
                if st.button("🚫 Cancel job", key=f"cancel_{rid}", disabled=not sure):
                    set_status(sb, r, "Cancelled", f"WO {wo} cancelled.")


def completed_view(sb, completed, load_error=None):
    """Closed Ventia jobs — out of the open list, still in the Term view."""
    with st.expander(f"✅ Completed Ventia jobs ({len(completed)})"):
        if load_error:
            st.error(f"⚠️ Couldn't load completed jobs: {load_error}")
            return
        if not completed:
            st.caption("Nothing has been marked completed yet.")
            return
        st.caption("Finished jobs, newest first. They still show in the Term view and the bookings list. "
                   "Use Reopen if one was marked completed by mistake.")
        for r in completed:
            rid = r["id"]
            wo = r.get("ventia_wo_number") or ""
            c1, c2 = st.columns([6, 1])
            with c1:
                line = f"**{r.get('priority') or '—'} · WO {wo}** — {build_public_summary(r.get('work_type',''), r.get('work_summary',''))}"
                extra = [x for x in (r.get("company_name"), _booking_when(r)) if x]
                st.write(line + (" · " + " · ".join(extra) if extra else ""))
            with c2:
                if st.button("↩️ Reopen", key=f"reopen_{rid}"):
                    set_status(sb, r, "Booked" if r.get("booking_date") else "Requested",
                               f"WO {wo} reopened — it is back in the open Ventia jobs list.")


# ---------------------------------------------------------------------------
# UI: List view (full detail — this tool only)
# ---------------------------------------------------------------------------

def list_view(sb):
    st.subheader("Upcoming & recent bookings")

    colf1, colf2, colf3 = st.columns(3)
    with colf1:
        range_choice = st.selectbox("Show", ["All", "Next 14 days", "This term (custom range)"])
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
            or s in (b.get("ventia_wo_number") or "").lower()
        ]

    if not bookings:
        st.info("No bookings found for this range.")
        return

    for b in bookings:
        header = f"{b['booking_date']} — {build_public_summary(b['work_type'], b['work_summary'])} — {b.get('company_name','')}"
        if b.get("ventia_wo_number"):
            header += f" — WO {b['ventia_wo_number']}"
        with st.expander(header):
            st.write(f"**Status:** {b.get('status','')}")
            if b.get("ventia_wo_number"):
                st.write(f"**Ventia WO:** {b['ventia_wo_number']}" + (f" ({b['priority']})" if b.get("priority") else ""))
            st.write(f"**Time:** {b.get('start_time','')} – {b.get('end_time','')}")
            st.write(f"**Location:** {b.get('location_onsite','')}")
            st.write(f"**Company:** {b.get('company_name','')}")
            st.write(f"**Contact:** {b.get('contact_name','')}"
                     + (f" — {b.get('contact_phone')}" if b.get('contact_phone') else "")
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

            colA, colM, colB = st.columns(3)
            with colA:
                if st.button("Edit", key=f"edit_{b['id']}"):
                    st.session_state["editing_booking"] = b
                    st.rerun()
            with colM:
                if b.get("status") in ("Booked", "Confirmed"):
                    if st.button("✅ Mark completed", key=f"complete_{b['id']}"):
                        set_status(sb, b, "Completed", "✅ Marked completed — it still shows in the Term view.")
                elif b.get("status") == "Completed":
                    if st.button("↩️ Reopen", key=f"reopenbk_{b['id']}"):
                        set_status(sb, b, "Booked", "Booking reopened.")
            with colB:
                if st.button("Delete", key=f"delete_{b['id']}"):
                    delete_booking(sb, b["id"])
                    flash("Booking deleted.")
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
    st.caption("Left-edge colour shows status: amber = Booked \u00b7 green = Confirmed \u00b7 grey with \u2713 = Completed \u00b7 red = Cancelled")

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
                    border_color = "#1A7A7A" if is_today else ("#9ca3af" if in_term else "#e5e7eb")
                    header_bg = "#1A7A7A" if is_today else ("#e5e9ea" if in_term else "#fafafa")
                    header_fg = "white" if is_today else ("#1f2937" if in_term else "#d1d5db")

                    if not in_term:
                        st.markdown(
                            f'<div style="border:2px solid {border_color};border-radius:8px;overflow:hidden;min-height:70px;">'
                            f'<div style="padding:.3rem .4rem;font-size:.72rem;font-weight:700;background:{header_bg};color:{header_fg};">'
                            f'{d.strftime("%a %-d %b")}</div></div>',
                            unsafe_allow_html=True,
                        )
                        continue

                    day_bookings = sorted(by_date.get(d.isoformat(), []), key=lambda x: str(x.get("start_time") or ""))
                    if not day_bookings:
                        body_html = '<div style="padding:.4rem;color:#c0c0c0;font-size:.7rem;">\u2014</div>'
                    else:
                        chips = ""
                        for b in day_bookings:
                            label = build_public_summary(b.get("work_type",""), b.get("work_summary",""))
                            status = b.get("status","")
                            t_str = ("✓ " if status == "Completed" else "") + (b.get("start_time") or "")[:5]
                            status_dot = {"Booked":"#e8a125","Confirmed":"#4a8f33","Completed":"#9ca3af","Cancelled":"#c0392b"}.get(status, "#9ca3af")
                            chips += (
                                f'<div style="background:#eef6f6;border-left:3px solid {status_dot};padding:.25rem .4rem;'
                                f'margin:.3rem .3rem 0;border-radius:4px;font-size:.68rem;line-height:1.25;">'
                                f'<strong>{t_str}</strong> {label}<br>'
                                f'<span style="color:#888;">{b.get("company_name","")}</span>'
                                + (f'<br><span style="color:#888;">WO {html.escape(str(b["ventia_wo_number"]))}'
                                   f'{" · " + html.escape(str(b["priority"])) if b.get("priority") else ""}</span>'
                                   if b.get("ventia_wo_number") else "")
                                + '</div>'
                            )
                        body_html = chips + '<div style="height:.3rem;"></div>'

                    st.markdown(
                        f'<div style="border:2px solid {border_color};border-radius:8px;overflow:hidden;'
                        f'box-shadow:0 1px 3px rgba(0,0,0,0.08);min-height:70px;">'
                        f'<div style="padding:.3rem .4rem;font-size:.72rem;font-weight:700;background:{header_bg};color:{header_fg};">'
                        f'{d.strftime("%a %-d %b")}</div>{body_html}</div>',
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

    # Result of the last save/update (shown after the rerun so it actually stays on screen)
    _flash = st.session_state.pop("_tb_flash", None)
    if _flash:
        (st.success if _flash[0] == "success" else st.error)(_flash[1])

    # While a booking or request is being edited, show only that form —
    # no tabs underneath, so it can't be missed or clash with the "new" forms.
    if "editing_booking" in st.session_state:
        booking_form(sb, existing=st.session_state["editing_booking"])
        if st.button("Cancel", key="cancel_edit_booking"):
            st.session_state.pop("editing_booking", None)
            st.rerun()
        return
    if "editing_request" in st.session_state:
        request_form(sb, existing=st.session_state["editing_request"])
        if st.button("Cancel", key="cancel_edit_request"):
            st.session_state.pop("editing_request", None)
            st.rerun()
        return

    try:
        open_requests, request_err = fetch_requests(sb), None
    except Exception as _req_err:
        open_requests, request_err = [], str(_req_err)

    try:
        completed_rows, completed_err = fetch_completed_requests(sb), None
    except Exception as _done_err:
        completed_rows, completed_err = [], str(_done_err)

    tab0, tab1, tab2, tab3 = st.tabs([
        f"📨 Ventia jobs ({len(open_requests)} open)", "📋 View bookings", "➕ Add booking", "🗓️ Term view",
    ])
    with tab0:
        with st.expander("➕ Lodge a new Ventia request", expanded=not open_requests):
            request_form(sb)
        requests_view(sb, open_requests, request_err)
        completed_view(sb, completed_rows, completed_err)
    with tab1:
        list_view(sb)
    with tab2:
        booking_form(sb)
    with tab3:
        term_view(sb)

try:
    main()
except Exception as _page_err:
    st.error("⚠️ Something went wrong loading this page — your sign-in should be unaffected. Details below:")
    st.exception(_page_err)

# ---------------------------------------------------------------------------
# DEPLOYMENT CHECKLIST
# ---------------------------------------------------------------------------
#
# 1) Run trade_bookings_schema.sql once in the SQL editor of the same
#    Supabase project your other tables (clc_events, pac_meetings, etc.)
#    already live in. If the trade_bookings table ALREADY exists (it does if
#    you've been using this tool), run trade_bookings_ventia_upgrade.sql
#    instead — it adds the Ventia work order / priority columns and lets
#    requests exist without a booking date.
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
