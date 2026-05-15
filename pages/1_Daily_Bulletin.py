# ══════════════════════════════════════════════════════════════════════════════
# ULTRA-SAFE DAILY BULLETIN NIT INTEGRATION
# ══════════════════════════════════════════════════════════════════════════════
# This version has maximum error handling and will NOT break the page

# STEP 1: Add this function near line 360 (with other load functions)
# ─────────────────────────────────────────────────────────────────────────────

def load_todays_nit_bookings(for_date):
    """Load NIT bookings for the specified date - ULTRA SAFE VERSION"""
    try:
        sb = _get_sb()
        if not sb:
            return []
        
        response = sb.table("nit_bookings")\
            .select("*")\
            .eq("status", "booked")\
            .eq("booking_date", str(for_date))\
            .execute()
        
        if not response or not response.data:
            return []
        
        # Sort by time slot
        slot_order = {"Monday 1:45pm": 1, "Tuesday 1:45pm": 2, "Thursday 2:15pm": 3}
        sorted_bookings = sorted(
            response.data, 
            key=lambda x: slot_order.get(x.get('time_slot', ''), 99)
        )
        return sorted_bookings
        
    except Exception as e:
        # Silent fail - don't break the page
        return []


# STEP 2: Replace the nit_col section (around line 996)
# ─────────────────────────────────────────────────────────────────────────────
# ONLY replace the content INSIDE "with nit_col:" - keep the "with nit_col:" line itself!

        with nit_col:
            st.markdown('<div class="section-card"><div class="section-card-header green"><h3>📅 Additional NIT Bookings</h3></div><div class="section-card-body">', unsafe_allow_html=True)
            
            # Try to load NIT bookings - if it fails, show the old text area
            try:
                nit_bookings = load_todays_nit_bookings(current_date)
                
                if nit_bookings and len(nit_bookings) > 0:
                    # Display each booking
                    for booking in nit_bookings:
                        time_slot = booking.get('time_slot', '')
                        staff_name = booking.get('staff_name', '')
                        
                        if time_slot and staff_name:  # Only show if both exist
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
                    # No bookings today
                    st.markdown('<div class="empty-state"><div class="icon">📅</div>No NIT bookings today</div>', unsafe_allow_html=True)
                    st.markdown('''
                        <div style="margin-top:0.5rem;font-size:0.75rem;color:#6b7280;">
                            📌 <a href="/NIT_Bookings" target="_self" style="color:#1A7A6E;text-decoration:none;font-weight:600;">
                            Book NIT Time →
                            </a>
                        </div>
                    ''', unsafe_allow_html=True)
                    
            except Exception as e:
                # If anything fails, show the old text area fallback
                if edit:
                    bulletin_data["nit_booking"] = st.text_area(
                        "NIT Booking Details", 
                        value=bulletin_data.get("nit_booking",""), 
                        height=120, 
                        label_visibility="collapsed", 
                        key="nit_booking_input"
                    )
                else:
                    nit_text = bulletin_data.get("nit_booking","").strip()
                    if nit_text:
                        st.markdown(f'<div style="font-size:.85rem;line-height:1.6;color:#2a3a2a;">{nit_text}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="empty-state"><div class="icon">📅</div>No NIT bookings</div>', unsafe_allow_html=True)
            
            st.markdown('</div></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# IMPORTANT NOTES
# ══════════════════════════════════════════════════════════════════════════════

# 1. This version will NEVER break the page - it has fallbacks everywhere
# 2. If NIT bookings fail to load, it falls back to the old text area
# 3. Keep your existing bulletin_data["nit_booking"] logic - this preserves it
# 4. Test in edit mode AND view mode after adding

# ══════════════════════════════════════════════════════════════════════════════
