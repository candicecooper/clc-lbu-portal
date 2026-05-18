import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from supabase import create_client
import os

# Page config
st.set_page_config(page_title="NIT Time Booking", page_icon="📅", layout="wide")

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

# Time slots configuration
TIME_SLOTS = {
    "Monday": "Monday 1:45pm",
    "Tuesday": "Tuesday 1:45pm",
    "Thursday": "Thursday 2:15pm"
}

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
    """Generate all valid booking dates (Mon, Tue, Thu only)"""
    start_date, end_date = get_booking_date_range()
    if not start_date or not end_date:
        return {}
    
    dates_by_slot = {slot: [] for slot in TIME_SLOTS.keys()}
    current_date = start_date
    
    while current_date <= end_date:
        day_name = current_date.strftime("%A")
        if day_name in TIME_SLOTS:
            dates_by_slot[day_name].append(current_date)
        current_date += timedelta(days=1)
    
    return dates_by_slot

def load_bookings():
    """Load all current bookings from Supabase"""
    try:
        response = supabase.table("nit_bookings").select("*").eq("status", "booked").execute()
        if response.data:
            df = pd.DataFrame(response.data)
            df['booking_date'] = pd.to_datetime(df['booking_date']).dt.date
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading bookings: {e}")
        return pd.DataFrame()

def load_staff_names():
    """Load staff names from database for admin dropdown"""
    try:
        response = supabase.table("staff").select("name").order("name").execute()
        if response.data:
            return [r["name"] for r in response.data]
        return []
    except Exception as e:
        st.warning(f"Could not load staff names: {e}")
        return []

def create_booking(booking_date, time_slot, staff_name):
    """Create a new booking"""
    try:
        data = {
            "booking_date": booking_date.isoformat(),
            "time_slot": time_slot,
            "staff_name": staff_name,
            "status": "booked"
        }
        response = supabase.table("nit_bookings").insert(data).execute()
        return True, "Booking created successfully!"
    except Exception as e:
        return False, f"Error creating booking: {e}"

def cancel_booking(booking_id):
    """Cancel a booking by deleting it"""
    try:
        response = supabase.table("nit_bookings").delete().eq("id", booking_id).execute()
        return True, "Booking cancelled successfully!"
    except Exception as e:
        return False, f"Error cancelling booking: {e}"

# Header
st.markdown(f"""
    <div style="background: linear-gradient(135deg, {PRIMARY_COLOR} 0%, {ACCENT_COLOR} 100%); 
                padding: 2rem; border-radius: 10px; margin-bottom: 2rem;">
        <h1 style="color: white; margin: 0;">📅 NIT Time Booking</h1>
        <p style="color: white; margin: 0.5rem 0 0 0; opacity: 0.9;">
            Book additional Non-Instructional Time for meetings
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
**Available Slots**: {', '.join(TIME_SLOTS.values())}  
**Duration**: 60 minutes additional NIT per booking
""")

# My Bookings Section
st.markdown("### 📋 My Bookings")

# Show admin badge if admin
if is_admin_user:
    st.markdown('<span style="background:#e8a125;color:#1a2e44;padding:0.25rem 0.75rem;border-radius:20px;font-size:0.75rem;font-weight:700;">👑 ADMIN</span>', unsafe_allow_html=True)
    st.caption("As an admin, you can book on behalf of any staff member")

# Staff name selection - dropdown for everyone
staff_list = load_staff_names()

if staff_list:
    # If authenticated, try to find their name in the list
    default_index = 0
    if staff_name and staff_name in staff_list:
        default_index = staff_list.index(staff_name) + 1  # +1 because we add empty option at start
    
    staff_name_filter = st.selectbox(
        "Select your name to view your bookings:",
        options=[""] + staff_list,
        index=default_index if staff_name else 0,
        key="staff_name_selector"
    )
    if staff_name_filter:
        st.caption("💡 Bookings will show if your name matches partially (e.g., 'Brenton' matches 'Brenton McGorman')")
else:
    # Fallback to text input if staff list can't be loaded
    if staff_name:
        staff_name_filter = staff_name
        st.info(f"Viewing bookings for: **{staff_name}**")
    else:
        staff_name_filter = st.text_input("Your name (to view/manage your bookings):", key="staff_filter")
        st.caption("⚠️ Could not load staff list - enter name manually")

if staff_name_filter:
    if not bookings_df.empty:
        # Flexible name matching - match if either name contains the other (case-insensitive)
        # This handles "Brenton" matching "Brenton McGorman" and vice versa
        filter_lower = staff_name_filter.lower()
        my_bookings = bookings_df[
            bookings_df['staff_name'].apply(
                lambda x: filter_lower in x.lower() or x.lower() in filter_lower
            )
        ]
    else:
        my_bookings = pd.DataFrame()  # Empty DataFrame if no bookings exist yet
    
    if not my_bookings.empty:
        my_bookings_sorted = my_bookings.sort_values('booking_date')
        
        st.markdown(f"**You have {len(my_bookings_sorted)} upcoming booking(s):**")
        
        for idx, booking in my_bookings_sorted.iterrows():
            col1, col2, col3 = st.columns([3, 3, 1])
            with col1:
                st.write(f"📅 {booking['booking_date'].strftime('%A, %d %B %Y')}")
            with col2:
                st.write(f"🕐 {booking['time_slot']}")
            with col3:
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

# Admin: Show all bookings
if is_admin_user:
    st.markdown("---")
    st.markdown("### 👑 All Bookings (Admin View)")
    
    if not bookings_df.empty:
        all_bookings_sorted = bookings_df.sort_values('booking_date')
        st.markdown(f"**Total of {len(all_bookings_sorted)} booking(s) in the system:**")
        
        for idx, booking in all_bookings_sorted.iterrows():
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            with col1:
                st.write(f"📅 {booking['booking_date'].strftime('%A, %d %B %Y')}")
            with col2:
                st.write(f"🕐 {booking['time_slot']}")
            with col3:
                st.write(f"👤 {booking['staff_name']}")
            with col4:
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

# Booking Grid
st.markdown("### 📅 Available Time Slots")

# Get all available dates
available_dates = get_available_dates()

if not available_dates:
    st.error("Unable to determine booking period. Please check term dates.")
else:
    # Group dates by week
    weeks = {}
    for day_name, dates in available_dates.items():
        for d in dates:
            week_start = d - timedelta(days=d.weekday())
            week_key = week_start.strftime("%d %b %Y")
            if week_key not in weeks:
                weeks[week_key] = {}
            weeks[week_key][day_name] = d
    
    # Display weeks
    for week_key in sorted(weeks.keys(), key=lambda x: datetime.strptime(x, "%d %b %Y")):
        week_data = weeks[week_key]
        
        # Week header
        st.markdown(f"#### Week of {week_key}")
        
        cols = st.columns(3)
        
        for idx, (day_name, time_slot_label) in enumerate(TIME_SLOTS.items()):
            with cols[idx]:
                if day_name in week_data:
                    booking_date = week_data[day_name]
                    
                    # Check if this slot is booked
                    if not bookings_df.empty:
                        existing_booking = bookings_df[
                            (bookings_df['booking_date'] == booking_date) & 
                            (bookings_df['time_slot'] == time_slot_label)
                        ]
                    else:
                        existing_booking = pd.DataFrame()  # Empty DataFrame if no bookings
                    
                    if not existing_booking.empty:
                        # Slot is booked
                        booked_by = existing_booking.iloc[0]['staff_name']
                        st.markdown(f"""
                            <div style="background-color: #E0E0E0; padding: 1rem; border-radius: 8px; 
                                        border-left: 4px solid #757575;">
                                <strong>{time_slot_label}</strong><br>
                                {booking_date.strftime('%d %b')}<br>
                                <span style="color: #757575;">Booked by: {booked_by}</span>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        # Slot is available
                        st.markdown(f"""
                            <div style="background-color: #E8F5E9; padding: 1rem; border-radius: 8px; 
                                        border-left: 4px solid {PRIMARY_COLOR};">
                                <strong>{time_slot_label}</strong><br>
                                {booking_date.strftime('%d %b')}<br>
                                <span style="color: {PRIMARY_COLOR};">✓ Available</span>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Booking form
                        with st.expander("Book this slot"):
                            if is_admin_user:
                                # Admin: Show dropdown with all staff names
                                staff_list = load_staff_names()
                                if staff_list:
                                    booking_staff_name = st.selectbox(
                                        "Select staff member:",
                                        options=[""] + staff_list,
                                        key=f"book_select_{booking_date}_{day_name}"
                                    )
                                else:
                                    booking_staff_name = st.text_input(
                                        "Staff name:",
                                        value="",
                                        key=f"book_{booking_date}_{day_name}"
                                    )
                                    st.caption("⚠️ Could not load staff list - enter name manually")
                            else:
                                # Regular staff: Pre-filled with their name
                                booking_staff_name = st.text_input(
                                    "Your name:", 
                                    value=staff_name if staff_name else (staff_name_filter if staff_name_filter else ""),
                                    key=f"book_{booking_date}_{day_name}"
                                )
                            
                            if st.button("Confirm Booking", key=f"confirm_{booking_date}_{day_name}"):
                                if booking_staff_name.strip():
                                    success, message = create_booking(booking_date, time_slot_label, booking_staff_name.strip())
                                    if success:
                                        st.success(message)
                                        st.rerun()
                                    else:
                                        st.error(message)
                                else:
                                    st.warning("Please enter your name")
                else:
                    # No date for this day in this week
                    st.markdown(f"""
                        <div style="background-color: #F5F5F5; padding: 1rem; border-radius: 8px; opacity: 0.5;">
                            <strong>{time_slot_label}</strong><br>
                            <span style="color: #757575;">Not available</span>
                        </div>
                    """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    <p>📞 Questions? Contact Candice or Annette | Built for CLC-LBU Staff</p>
</div>
""", unsafe_allow_html=True)
