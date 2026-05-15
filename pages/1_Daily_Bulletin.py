# ══════════════════════════════════════════════════════════════════════════════
# NIT BOOKINGS INTEGRATION FOR DAILY BULLETIN
# ══════════════════════════════════════════════════════════════════════════════
# Replace the existing NIT booking section (around line 997-1003) with this code:

def load_todays_nit_bookings(for_date):
    """Load NIT bookings for the specified date"""
    try:
        sb = _get_sb()
        response = sb.table("nit_bookings")\
            .select("*")\
            .eq("status", "booked")\
            .eq("booking_date", str(for_date))\
            .execute()
        
        if response.data:
            # Sort by time slot
            slot_order = {"Monday 1:45pm": 1, "Tuesday 1:45pm": 2, "Thursday 2:15pm": 3}
            sorted_bookings = sorted(response.data, 
                                   key=lambda x: slot_order.get(x.get('time_slot', ''), 99))
            return sorted_bookings
        return []
    except Exception as e:
        st.warning(f"⚠️ Could not load NIT bookings: {e}")
        return []

# Then in the nit_col section (around line 996-1003), replace with:

        with nit_col:
            st.markdown('<div class="section-card"><div class="section-card-header green"><h3>📅 Additional NIT Bookings</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            
            # Load today's bookings from database
            nit_bookings = load_todays_nit_bookings(current_date)
            
            if nit_bookings:
                # Display each booking
                for booking in nit_bookings:
                    time_slot = booking.get('time_slot', '')
                    staff_name = booking.get('staff_name', '')
                    
                    st.markdown(f'''
                        <div style="background:#E8F5E9;padding:0.75rem;margin:0.5rem 0;
                                    border-radius:8px;border-left:4px solid #1A7A6E;">
                            <div style="font-weight:700;color:#1A7A6E;font-size:0.9rem;">
                                🕐 {time_slot}
                            </div>
                            <div style="font-size:0.85rem;color:#2d6b1a;margin-top:0.2rem;">
                                {staff_name}
                            </div>
                        </div>
                    ''', unsafe_allow_html=True)
                
                # Link to booking page
                st.markdown('''
                    <div style="margin-top:0.75rem;font-size:0.75rem;color:#6b7280;">
                        📌 <a href="/NIT_Bookings" target="_self" style="color:#1A7A6E;text-decoration:none;font-weight:600;">
                        Manage NIT Bookings →
                        </a>
                    </div>
                ''', unsafe_allow_html=True)
            else:
                st.markdown('<div class="empty-state"><div class="icon">📅</div>No NIT bookings today</div>', unsafe_allow_html=True)
                
                # Still show link to booking page
                st.markdown('''
                    <div style="margin-top:0.5rem;font-size:0.75rem;color:#6b7280;">
                        📌 <a href="/NIT_Bookings" target="_self" style="color:#1A7A6E;text-decoration:none;font-weight:600;">
                        Book NIT Time →
                        </a>
                    </div>
                ''', unsafe_allow_html=True)
            
            st.markdown('</div></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION NOTES:
# 1. Add load_todays_nit_bookings() function near the other load functions (around line 360)
# 2. Replace the nit_col section (lines 996-1003) with the code above
# 3. Make sure _get_sb() is available (it is - used in other load functions)
# ══════════════════════════════════════════════════════════════════════════════
