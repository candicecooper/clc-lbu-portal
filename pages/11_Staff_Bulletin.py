# ══════════════════════════════════════════════════════════════════════════════
# NIT BOOKINGS INTEGRATION FOR STAFF BULLETIN
# ══════════════════════════════════════════════════════════════════════════════

def load_upcoming_nit_bookings():
    """Load NIT bookings for the next 2 weeks"""
    try:
        from datetime import date, timedelta
        today = date.today()
        two_weeks = today + timedelta(weeks=2)
        
        sb = get_sb()
        response = sb.table("nit_bookings")\
            .select("*")\
            .eq("status", "booked")\
            .gte("booking_date", str(today))\
            .lte("booking_date", str(two_weeks))\
            .execute()
        
        if response.data:
            import pandas as pd
            df = pd.DataFrame(response.data)
            df['booking_date'] = pd.to_datetime(df['booking_date']).dt.date
            
            # Sort by date then time slot
            slot_order = {"Monday 1:45pm": 1, "Tuesday 1:45pm": 2, "Thursday 2:15pm": 3}
            df['slot_sort'] = df['time_slot'].map(lambda x: slot_order.get(x, 99))
            df = df.sort_values(['booking_date', 'slot_sort'])
            
            return df.to_dict('records')
        return []
    except Exception as e:
        st.warning(f"⚠️ Could not load NIT bookings: {e}")
        return []

def render_nit_bookings_section():
    """Render the NIT bookings section in the Staff Bulletin"""
    nit_bookings = load_upcoming_nit_bookings()
    
    if not nit_bookings:
        return  # Don't show section if no bookings
    
    st.markdown('''
        <div style="background:linear-gradient(135deg,#1A7A6E,#2d9e7d);
                    border-radius:12px;padding:18px 24px;margin:24px 0;">
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                        letter-spacing:0.1em;color:rgba(255,255,255,0.6);margin-bottom:6px;">
                NIT Time Bookings
            </div>
            <div style="font-size:20px;font-weight:800;color:white;">
                📅 Upcoming Additional NIT
            </div>
            <div style="font-size:13px;color:rgba(255,255,255,0.7);margin-top:4px;">
                Next 2 weeks · Staff can book via portal
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    # Group by date
    from collections import defaultdict
    by_date = defaultdict(list)
    for booking in nit_bookings:
        by_date[booking['booking_date']].append(booking)
    
    # Display each date
    for booking_date in sorted(by_date.keys()):
        date_bookings = by_date[booking_date]
        
        # Format date header
        day_name = booking_date.strftime("%A")
        date_str = booking_date.strftime("%-d %B")
        
        st.markdown(f'''
            <div style="font-size:14px;font-weight:700;color:var(--ink);
                        margin:16px 0 8px 0;padding-bottom:4px;
                        border-bottom:2px solid var(--border);">
                {day_name}, {date_str}
            </div>
        ''', unsafe_allow_html=True)
        
        for booking in date_bookings:
            time_slot = booking['time_slot']
            staff_name = booking['staff_name']
            
            st.markdown(f'''
                <div style="background:#FFF3E0;border-left:3px solid #C8760A;
                            border-radius:8px;padding:12px 16px;margin-bottom:8px;">
                    <div style="font-weight:700;color:#C8760A;font-size:14px;">
                        🕐 {time_slot}
                    </div>
                    <div style="font-size:13px;color:#8c6a4f;margin-top:4px;">
                        {staff_name}
                    </div>
                </div>
            ''', unsafe_allow_html=True)
    
    # Link to booking page
    st.markdown('''
        <div style="text-align:center;margin-top:16px;padding-top:12px;
                    border-top:1px solid var(--border);">
            <a href="/NIT_Bookings" target="_self" 
               style="color:#1A7A6E;text-decoration:none;font-weight:600;font-size:13px;">
                📌 View or Book NIT Time →
            </a>
        </div>
    ''', unsafe_allow_html=True)
    
    st.write("")

# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION INSTRUCTIONS:
# ══════════════════════════════════════════════════════════════════════════════
# 1. Add the load_upcoming_nit_bookings() function near other db functions (around line 200)
# 2. Add the render_nit_bookings_section() function near other render functions (around line 670)
# 3. Call render_nit_bookings_section() in the render_bulletin() function
#    RIGHT AFTER the notices loop (after line 725, before the acknowledgement section)
#
# Insert this code in render_bulletin() function:
#
#     for n in notices:
#         # ... existing notice rendering code ...
#
#     # ADD THIS SECTION HERE:
#     st.write("")
#     render_nit_bookings_section()
#     
#     if show_ack:
#         # ... existing acknowledgement code ...
#
# ══════════════════════════════════════════════════════════════════════════════
