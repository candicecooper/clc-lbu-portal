# ════════════════════════════════════════════════════════════════════════════
# 1_Daily_Bulletin.py — TWO TARGETED FIXES
# Apply both changes in GitHub then commit
# ════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# FIX 1 — Staff Room button (already correct in your file — no change needed)
# The button in ctrl_cols[4] already reads:
#   'https://clcdailybulletin.streamlit.app/?display=true'
# If the button is not working, it's likely a Streamlit rendering issue
# with the anchor tag. Replace the HTML anchor with a proper st.link_button.
#
# FIND this block in ctrl_cols[4] (around the edit controls section):
#
#   with ctrl_cols[4]:
#       st.markdown('<a href="https://clcdailybulletin.streamlit.app/?display=true" ...
#
# REPLACE with:
# ─────────────────────────────────────────────────────────────────────────────

    with ctrl_cols[4]:
        st.link_button(
            "📺 Staff Room",
            "https://clcdailybulletin.streamlit.app/?display=true",
            use_container_width=True
        )

# ─────────────────────────────────────────────────────────────────────────────
# FIX 2 — Program Changes not appearing in display mode
#
# ROOT CAUSE: The display mode was building one giant HTML string containing
# nested <table> elements inside a <div> and passing it all to one
# st.markdown() call. Streamlit's markdown parser sanitises complex nested
# HTML tables, so the timetable grid was silently stripped.
#
# FIX: Split into separate st.markdown() calls — one per change.
#
# IN THE DISPLAY MODE SECTION (after the r2 columns, before the clock script),
# FIND this entire block:
#
#   bc_today = load_bulletin_changes(today)
#   if bc_today:
#       pc_parts = []
#       for ch in bc_today:
#           ...
#           pc_parts.append(...)
#       st.markdown(
#           f'<div class="dp">...<div class="dp-body">{"".join(pc_parts)}</div></div>',
#           unsafe_allow_html=True)
#   else:
#       st.markdown('<div class="dp">...No program changes today...</div>', ...)
#
# REPLACE THE ENTIRE BLOCK with the code below:
# ─────────────────────────────────────────────────────────────────────────────

    # Program Changes — separate st.markdown() calls avoid Streamlit HTML sanitisation
    bc_today = load_bulletin_changes(today)
    st.markdown('<div class="dp"><div class="dp-header green">📊 Program Changes</div>', unsafe_allow_html=True)
    if bc_today:
        for ch in bc_today:
            reason     = ch.get("reason","")
            absent     = ch.get("staff_absent","")
            has_trt    = ch.get("has_trt", False)
            trt_name   = ch.get("trt_name","")
            staff_rows = ch.get("staff_rows",[])
            color      = "#dc2626" if reason == "Staff Absence" else "#0e7490"
            meta_parts = []
            if absent:  meta_parts.append(f"Absent: <strong>{absent}</strong>")
            if has_trt: meta_parts.append(f"TRT: {trt_name or 'On site'}")
            meta_str = " &nbsp;·&nbsp; ".join(meta_parts)

            # Change header row
            st.markdown(
                f'<div class="dp-body" style="border-left:3px solid {color};'
                f'padding:.3rem .5rem .1rem .75rem;margin-bottom:2px;">'
                f'<div style="font-size:.6rem;color:#5a7a8a;font-weight:700;letter-spacing:.06em;">'
                f'{reason.upper()}{(" &nbsp;·&nbsp; " + meta_str) if meta_str else ""}</div></div>',
                unsafe_allow_html=True
            )

            # Timetable grid in its OWN st.markdown() call
            tt_html = _timetable_grid_html(staff_rows, PC_TIME_SLOTS_30, dark=False)
            if tt_html:
                st.markdown(
                    f'<div class="dp-body" style="padding:.2rem .5rem .4rem;overflow-x:auto;">{tt_html}</div>',
                    unsafe_allow_html=True
                )
            else:
                # Fallback: block badges so something always appears
                any_blocks = False
                for row in staff_rows:
                    name   = row.get("name","")
                    blocks = row.get("blocks",[])
                    if not blocks:
                        continue
                    any_blocks = True
                    badges = " ".join([
                        f'<span style="background:{_slot_color_bg(b.get("role",""))};'
                        f'color:{_slot_color_fg(b.get("role",""))};'
                        f'padding:1px 7px;border-radius:8px;font-size:.7rem;font-weight:600;margin:1px;">'
                        f'{b.get("start","")}–{b.get("end","")} {b.get("role","")}'
                        + (f' → {b["person"]}' if b.get("person") and b.get("role")=="Lunch Cover" else "")
                        + (f' ↩ {b["person"]}' if b.get("person") and b.get("role")=="Lunch Break" else "")
                        + '</span>'
                        for b in blocks if b.get("role") or b.get("start")
                    ])
                    if badges:
                        st.markdown(
                            f'<div class="dp-body" style="padding:.15rem .5rem .15rem .75rem;">'
                            f'<span style="font-size:.7rem;font-weight:700;color:#2a3a2a;">{name}: </span>'
                            f'{badges}</div>',
                            unsafe_allow_html=True
                        )
                if not any_blocks:
                    st.markdown(
                        '<div class="dp-body"><span style="color:#9ab09a;font-size:.7rem;'
                        'font-style:italic;">No timetable recorded.</span></div>',
                        unsafe_allow_html=True
                    )
        st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="dp-body"><span style="color:#9ab09a;font-size:.7rem;'
            'font-style:italic;">No program changes today.</span></div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)   # close .dp

# ─────────────────────────────────────────────────────────────────────────────
# NOTE: The live clock script and st.stop() that follow remain unchanged.
# ─────────────────────────────────────────────────────────────────────────────
