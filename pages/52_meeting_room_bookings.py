import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from supabase import create_client
import os

# Page config
st.set_page_config(page_title="Meeting Room Booking", page_icon="🗓️", layout="wide")

# Auth check with fallback
try:
    from auth import get_staff_name, is_admin
    staff_name = get_staff_name()
    is_admin_user = is_admin()
except Exception as e:
    st.warning(f"Auth module error: {e}")
    staff_name = None
    is_admin_user = False

# Debug info (comment out in production)
if st.session_state.get('show_debug', False):
    st.info(f"Debug: staff_name = {staff_name}, is_admin = {is_admin_user}")

# Manual admin override for testing (remove in production)
with st.sidebar:
    st.markdown("### 🔧 Admin Access")
    if st.checkbox("Enable Admin Mode (for testing)", key="admin_override"):
        is_admin_user = True
        st.success("Admin mode enabled!")
    st.checkbox("Show Debug Info", key="show_debug")

# Supabase setup
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# CLC Branding colors
PRIMARY_COLOR = "#1A7A6E"  # Teal
ACCENT_COLOR = "#C8760A"  # Amber

# Room name (single shared meeting room)
ROOM_NAME = "Meeting Room"

# Staff to always include in the dropdown, even if not yet in the staff table
ADDITIONAL_STAFF = ["Roisin"]

# Hour-block time slots: 8:00am start through to the last bookable start of 4:00pm
# (so the room can be occupied through to 5:00pm on that final slot).
HOUR_SLOTS = [
    {"start": "08:00", "label": "8:00 - 9:00am"},
    {"start": "09:00", "label": "9:00 - 10:00am"},
    {"start": "10:00", "label": "10:00 - 11:00am"},
    {"start": "11:00", "label": "11:00am - 12:00pm"},
    {"start": "12:00", "label": "12:00 - 1:00pm"},
    {"start": "13:00", "label": "1:00 - 2:00pm"},
    {"start": "14:00", "label": "2:00 - 3:00pm"},
    {"start": "15:00", "label": "3:00 - 4:00pm"},
    {"start": "16:00", "label": "4:00 - 5:00pm"},
]
SLOT_LABELS = [s["label"] for s in HOUR_SLOTS]
SLOT_ORDER = {s["label"]: i for i, s in enumerate(HOUR_SLOTS)}

# Term dates for 2026 (South Australia)
TERM_DATES = {
    "Term 1": {"start": date(2026, 1, 27), "end": date(2026, 4, 10)},
    "Term 2": {"start": date(2026, 5, 18), "end": date(2026, 7, 3)},
    "Term 3": {"start": date(2026, 7, 20), "end": date(2026, 9, 25)},
    "Term 4": {"start": date(2026, 10, 12), "end": date(2026, 12, 11)},
}

def get_current_term():
    """Determine which term we're currently in"""
    today = date.today()
    for term_name, dates in TERM_DATES.items():
        if dates["start"] <= today <= dates["end"]:
            return term_name, dates["start"], dates["end"]
    return None, None, None

def get_booking_date_range():
    """Get the date range for bookings (current term + 5 weeks of next term)"""
    today = date.today()
    current_term, term_start, term_end = get_current_term()

    # If we're before Term 2 starts, use Term 2 start date
    if not current_term or today < TERM_DATES["Term 2"]["start"]:
        term_start = TERM_DATES["Term 2"]["start"]
        term_end = TERM_DATES["Term 2"]["end"]
        current_term = "Term 2"

    # End date is 5 weeks into next term
    next_term_start = None
    terms_list = list(TERM_DATES.items())
    for i, (term_name, _) in enumerate(terms_list):
        if term_name == current_term and i < len(terms_list) - 1:
            next_term_start = terms_list[i + 1][1]["start"]
            break

    if next_term_start:
        end_date = next_term_start + timedelta(weeks=5)
    else:
        end_date = term_end

    return term_start, end_date

def get_available_dates():
    """Generate all valid booking dates (Mon-Fri only)"""
    start_date, end_date = get_booking_date_range()
    if not start_date or not end_date:
        return []

    dates = []
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5:  # Monday=0 ... Friday=4
            dates.append(current_date)
        current_date += timedelta(days=1)

    return dates

def load_bookings():
    """Load all current bookings from Supabase"""
    try:
        response = supabase.table("meeting_room_bookings").select("*").eq("status", "booked").execute()
        if response.data:
            df = pd.DataFrame(response.data)
            df['booking_date'] = pd.to_datetime(df['booking_date']).dt.date
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading bookings: {e}")
        return pd.DataFrame()

def load_staff_names():
    """Load staff names from database for dropdowns, always including ADDITIONAL_STAFF"""
    try:
        response = supabase.table("staff").select("name").order("name").execute()
        names = [r["name"] for r in response.data] if response.data else []
    except Exception as e:
        st.warning(f"Could not load staff names: {e}")
        names = []

    # Add any additional staff not already present (partial match check)
    for extra in ADDITIONAL_STAFF:
        if not any(extra.lower() in n.lower() for n in names):
            names.append(extra)

    return sorted(names)

def load_staff_records():
    """Load staff as (id, name) records for the admin Manage Staff panel"""
    try:
        response = supabase.table("staff").select("id, name").order("name").execute()
        return response.data or []
    except Exception as e:
        st.warning(f"Could not load staff records: {e}")
        return []

def add_staff_member(name):
    """Add a new staff member to the shared staff table"""
    try:
        supabase.table("staff").insert({"name": name}).execute()
        return True, "Staff member added successfully!"
    except Exception as e:
        return False, f"Error adding staff member: {e}"

def update_staff_member(staff_id, new_name):
    """Rename an existing staff member"""
    try:
        supabase.table("staff").update({"name": new_name}).eq("id", staff_id).execute()
        return True, "Staff member updated successfully!"
    except Exception as e:
        return False, f"Error updating staff member: {e}"

def create_booking(booking_date, time_slot, staff_name, purpose=""):
    """Create a new booking"""
    try:
        data = {
            "booking_date": booking_date.isoformat(),
            "time_slot": time_slot,
            "staff_name": staff_name,
            "purpose": purpose,
            "status": "booked"
        }
        response = supabase.table("meeting_room_bookings").insert(data).execute()
        return True, "Booking created successfully!"
    except Exception as e:
        return False, f"Error creating booking: {e}"

def cancel_booking(booking_id):
    """Cancel a booking by deleting it"""
    try:
        response = supabase.table("meeting_room_bookings").delete().eq("id", booking_id).execute()
        return True, "Booking cancelled successfully!"
    except Exception as e:
        return False, f"Error cancelling booking: {e}"

# Header
st.markdown(f"""
    <div style="background: linear-gradient(135deg, {PRIMARY_COLOR} 0%, {ACCENT_COLOR} 100%);
                padding: 2rem; border-radius: 10px; margin-bottom: 2rem;">
        <h1 style="color: white; margin: 0;">🗓️ {ROOM_NAME} Booking</h1>
        <p style="color: white; margin: 0.5rem 0 0 0; opacity: 0.9;">
            Book the meeting room in one-hour blocks, Monday to Friday
        </p>
    </div>
""", unsafe_allow_html=True)

# Load current bookings
bookings_df = load_bookings()

# Current term info
current_term, term_start, term_end = get_current_term()
booking_start, booking_end = get_booking_date_range()

# If we're before Term 2, show appropriate message
today = date.today()
if today < TERM_DATES["Term 2"]["start"]:
    period_text = f"Term 2 bookings (starts {TERM_DATES['Term 2']['start'].strftime('%d %B %Y')})"
else:
    period_text = f"{current_term} (viewing until {booking_end.strftime('%d %B %Y')})"

st.info(f"""
**Current Period**: {period_text}
**Available Days**: Monday to Friday
**Available Hours**: 8:00am - 5:00pm, in 1 hour blocks (last booking starts at 4:00pm)
""")

# ── My Bookings Section ──────────────────────────────────────
st.markdown("### 📋 My Bookings")

if is_admin_user:
    st.markdown('<span style="background:#e8a125;color:#1a2e44;padding:0.25rem 0.75rem;border-radius:20px;font-size:0.75rem;font-weight:700;">👑 ADMIN</span>', unsafe_allow_html=True)
    st.caption("As an admin, you can book on behalf of any staff member")

staff_list = load_staff_names()

if staff_list:
    default_index = 0
    if staff_name and staff_name in staff_list:
        default_index = staff_list.index(staff_name) + 1
    staff_name_filter = st.selectbox(
        "Select your name to view your bookings:",
        options=[""] + staff_list,
        index=default_index if staff_name else 0,
        key="staff_name_selector"
    )
    if staff_name_filter:
        st.caption("💡 Bookings will show if your name matches partially (e.g., 'Brenton' matches 'Brenton McGorman')")
else:
    if staff_name:
        staff_name_filter = staff_name
        st.info(f"Viewing bookings for: **{staff_name}**")
    else:
        staff_name_filter = st.text_input("Your name (to view/manage your bookings):", key="staff_filter")
        st.caption("⚠️ Could not load staff list - enter name manually")

if staff_name_filter:
    if not bookings_df.empty:
        filter_lower = staff_name_filter.lower()
        my_bookings = bookings_df[
            bookings_df['staff_name'].apply(
                lambda x: filter_lower in x.lower() or x.lower() in filter_lower
            )
        ]
    else:
        my_bookings = pd.DataFrame()

    if not my_bookings.empty:
        my_bookings = my_bookings.copy()
        my_bookings["_slot_order"] = my_bookings["time_slot"].apply(lambda x: SLOT_ORDER.get(x, 99))
        my_bookings_sorted = my_bookings.sort_values(["booking_date", "_slot_order"])

        st.markdown(f"**You have {len(my_bookings_sorted)} upcoming booking(s):**")

        for idx, booking in my_bookings_sorted.iterrows():
            col1, col2, col3, col4 = st.columns([2, 2, 3, 1])
            with col1:
                st.write(f"📅 {booking['booking_date'].strftime('%A, %d %B %Y')}")
            with col2:
                st.write(f"🕐 {booking['time_slot']}")
            with col3:
                st.write(f"📝 {booking.get('purpose', '') or '—'}")
            with col4:
                if st.button("Cancel", key=f"cancel_{booking['id']}"):
                    success, message = cancel_booking(booking['id'])
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
        st.markdown("---")
    else:
        st.info("You have no upcoming bookings.")
else:
    st.info("👆 Enter your name above to view and manage your bookings")

# ── Admin: Show all bookings ─────────────────────────────────
if is_admin_user:
    st.markdown("---")
    st.markdown("### 👑 All Bookings (Admin View)")

    if not bookings_df.empty:
        all_bookings_sorted = bookings_df.copy()
        all_bookings_sorted["_slot_order"] = all_bookings_sorted["time_slot"].apply(lambda x: SLOT_ORDER.get(x, 99))
        all_bookings_sorted = all_bookings_sorted.sort_values(["booking_date", "_slot_order"])
        st.markdown(f"**Total of {len(all_bookings_sorted)} booking(s) in the system:**")

        for idx, booking in all_bookings_sorted.iterrows():
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
            with col1:
                st.write(f"📅 {booking['booking_date'].strftime('%A, %d %B %Y')}")
            with col2:
                st.write(f"🕐 {booking['time_slot']}")
            with col3:
                st.write(f"👤 {booking['staff_name']}")
            with col4:
                st.write(f"📝 {booking.get('purpose', '') or '—'}")
            with col5:
                if st.button("Cancel", key=f"admin_cancel_{booking['id']}"):
                    success, message = cancel_booking(booking['id'])
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
    else:
        st.info("No bookings in the system yet")

    st.markdown("---")

    # ── Admin: Manage Staff ──────────────────────────────────
    st.markdown("### 🧑‍💼 Manage Staff")
    st.caption("This staff list is shared across the portal (NIT Booking, Meeting Room Booking, etc.) — changes here apply everywhere.")

    staff_records = load_staff_records()

    if staff_records:
        for record in staff_records:
            scol1, scol2 = st.columns([4, 1])
            with scol1:
                edited_name = st.text_input(
                    "Name",
                    value=record.get("name", ""),
                    key=f"staff_edit_{record['id']}",
                    label_visibility="collapsed"
                )
            with scol2:
                if st.button("Save", key=f"staff_save_{record['id']}"):
                    new_name = edited_name.strip()
                    if not new_name:
                        st.warning("Name cannot be empty")
                    elif new_name == record.get("name", ""):
                        st.info("No changes to save")
                    else:
                        success, message = update_staff_member(record["id"], new_name)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
    else:
        st.info("No staff members found in the database yet.")

    st.markdown("**Add a new staff member:**")
    acol1, acol2 = st.columns([4, 1])
    with acol1:
        new_staff_name = st.text_input(
            "New staff name", key="new_staff_name",
            label_visibility="collapsed", placeholder="e.g. Jamie Smith"
        )
    with acol2:
        if st.button("➕ Add", key="add_staff_btn"):
            if new_staff_name.strip():
                success, message = add_staff_member(new_staff_name.strip())
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.warning("Please enter a name")

    st.markdown("---")

# ── Weekly overview (read-only) ──────────────────────────────
st.markdown("### 📊 Weekly Overview")

available_dates = get_available_dates()

if not available_dates:
    st.error("Unable to determine booking period. Please check term dates.")
else:
    weeks = {}
    for d in available_dates:
        week_start = d - timedelta(days=d.weekday())
        week_key = week_start
        weeks.setdefault(week_key, []).append(d)

    week_keys_sorted = sorted(weeks.keys())
    week_labels = [f"Week of {wk.strftime('%d %b %Y')}" for wk in week_keys_sorted]

    if "mrb_week_idx" not in st.session_state:
        # Default to the week containing today, or the first available week
        default_idx = 0
        for i, wk in enumerate(week_keys_sorted):
            if wk <= today < wk + timedelta(days=7):
                default_idx = i
                break
        st.session_state.mrb_week_idx = default_idx

    nav1, nav2, nav3 = st.columns([1, 4, 1])
    with nav1:
        if st.button("← Prev week", disabled=st.session_state.mrb_week_idx <= 0):
            st.session_state.mrb_week_idx -= 1
            st.rerun()
    with nav2:
        st.markdown(f"<div style='text-align:center;font-weight:700;color:{PRIMARY_COLOR};'>{week_labels[st.session_state.mrb_week_idx]}</div>", unsafe_allow_html=True)
    with nav3:
        if st.button("Next week →", disabled=st.session_state.mrb_week_idx >= len(week_keys_sorted) - 1):
            st.session_state.mrb_week_idx += 1
            st.rerun()

    week_key = week_keys_sorted[st.session_state.mrb_week_idx]
    week_dates = weeks[week_key]

    def _booked_lookup(d, slot_label):
        if bookings_df.empty:
            return None
        match = bookings_df[(bookings_df['booking_date'] == d) & (bookings_df['time_slot'] == slot_label)]
        if not match.empty:
            return match.iloc[0]['staff_name']
        return None

    header_cells = "".join([f'<th style="background:#f4f8f2;color:#4a6640;font-size:.72rem;padding:.4rem .5rem;border-bottom:2px solid #d8ead2;">{d.strftime("%a %d %b")}</th>' for d in week_dates])
    rows_html = ""
    for slot in HOUR_SLOTS:
        cells = ""
        for d in week_dates:
            booked_by = _booked_lookup(d, slot["label"])
            if booked_by:
                cells += f'<td style="padding:.4rem .5rem;background:#F0F0F0;border-bottom:1px solid #e5e5e5;color:#757575;font-size:.72rem;">🔒 {booked_by}</td>'
            else:
                cells += f'<td style="padding:.4rem .5rem;background:#E8F5E9;border-bottom:1px solid #e5e5e5;color:{PRIMARY_COLOR};font-size:.72rem;">✓ Available</td>'
        rows_html += f'<tr><td style="padding:.4rem .5rem;font-weight:700;font-size:.72rem;color:#1a2e44;white-space:nowrap;border-bottom:1px solid #e5e5e5;">{slot["label"]}</td>{cells}</tr>'

    st.markdown(
        f'<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr><th style="background:#f4f8f2;padding:.4rem .5rem;border-bottom:2px solid #d8ead2;"></th>{header_cells}</tr></thead>'
        f'<tbody>{rows_html}</tbody></table></div>',
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Book a slot ───────────────────────────────────────────
    st.markdown("### ✅ Book a Slot")

    date_options = {d.strftime("%A, %d %B %Y"): d for d in available_dates}
    chosen_label = st.selectbox("Choose a date:", options=list(date_options.keys()), key="mrb_book_date")
    chosen_date = date_options[chosen_label]

    cols = st.columns(3)
    for i, slot in enumerate(HOUR_SLOTS):
        with cols[i % 3]:
            booked_by = _booked_lookup(chosen_date, slot["label"])
            if booked_by:
                st.markdown(f"""
                    <div style="background-color: #E0E0E0; padding: 1rem; border-radius: 8px;
                                border-left: 4px solid #757575; margin-bottom: 0.75rem;">
                        <strong>{slot['label']}</strong><br>
                        <span style="color: #757575;">Booked by: {booked_by}</span>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div style="background-color: #E8F5E9; padding: 1rem; border-radius: 8px;
                                border-left: 4px solid {PRIMARY_COLOR}; margin-bottom: 0.5rem;">
                        <strong>{slot['label']}</strong><br>
                        <span style="color: {PRIMARY_COLOR};">✓ Available</span>
                    </div>
                """, unsafe_allow_html=True)

                with st.expander("Book this slot"):
                    if is_admin_user:
                        staff_list = load_staff_names()
                        if staff_list:
                            booking_staff_name = st.selectbox(
                                "Select staff member:",
                                options=[""] + staff_list,
                                key=f"book_select_{chosen_date}_{slot['start']}"
                            )
                        else:
                            booking_staff_name = st.text_input(
                                "Staff name:",
                                value="",
                                key=f"book_{chosen_date}_{slot['start']}"
                            )
                            st.caption("⚠️ Could not load staff list - enter name manually")
                    else:
                        booking_staff_name = st.text_input(
                            "Your name:",
                            value=staff_name if staff_name else (staff_name_filter if staff_name_filter else ""),
                            key=f"book_{chosen_date}_{slot['start']}"
                        )

                    purpose = st.text_input(
                        "Purpose (optional):",
                        key=f"purpose_{chosen_date}_{slot['start']}"
                    )

                    if st.button("Confirm Booking", key=f"confirm_{chosen_date}_{slot['start']}"):
                        if booking_staff_name.strip():
                            success, message = create_booking(chosen_date, slot['label'], booking_staff_name.strip(), purpose.strip())
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                        else:
                            st.warning("Please enter your name")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    <p>📞 Questions? Contact Candice or Annette | Built for CLC-LBU Staff</p>
</div>
""", unsafe_allow_html=True)
