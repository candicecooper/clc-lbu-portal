from theme import apply_clc_theme
import streamlit as st
from supabase import create_client
import datetime

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Submit Agenda Item | CLC-LBU", page_icon="📝", layout="wide")
apply_clc_theme()

from auth import require_auth, logout_button, get_staff_name
require_auth("Submit Agenda Item", "📝")
logout_button("sidebar")

# ── Back to Portal ─────────────────────────────────────────────────────────────
st.sidebar.markdown(
    '<a href="https://16cefb77.clc-portal.pages.dev/" target="_self" style="display:block;text-align:center;'
    'background:#1A7A7A;color:white;font-weight:600;font-size:0.85rem;'
    'padding:0.5rem;border-radius:8px;text-decoration:none;margin-bottom:0.5rem;">'
    '🏠 Back to Staff Portal</a>',
    unsafe_allow_html=True
)

# ── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
SUPABASE_SERVICE_KEY = st.secrets.get("SUPABASE_SERVICE_KEY", SUPABASE_KEY)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════

st.title("📝 Submit STAFF Meeting Agenda Item")
st.caption("Quick submission for upcoming staff meeting agenda")
st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# QUICK SUBMISSION FORM
# ══════════════════════════════════════════════════════════════════════════════

col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("Submit an Agenda Item")
    
    staff_name = get_staff_name()
    
    agenda_item = st.text_area(
        "Your Agenda Item",
        height=120,
        placeholder="Describe the agenda item you'd like discussed at the next staff meeting...",
        key="agenda_item"
    )
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        term = st.text_input("Term (optional)", placeholder="T1, T2, etc.", key="term")
    
    with col_b:
        week_number = st.number_input("Week Number (optional)", min_value=0, max_value=11, value=0, key="week")
    
    category = st.selectbox(
        "Category (optional)",
        options=["", "WHS", "Finance", "Social Club", "Policy", "Curriculum", "Other"],
        key="category"
    )
    
    if st.button("📤 Submit Agenda Item", type="primary", use_container_width=True):
        if agenda_item.strip():
            try:
                submission_data = {
                    "submitted_by": staff_name,
                    "item_text": agenda_item.strip(),
                    "date_submitted": str(datetime.date.today()),
                    "week_number": week_number if week_number > 0 else None,
                    "term": term.strip() if term.strip() else None,
                    "status": "pending",
                    "category": category if category else None
                }
                
                result = supabase.table('staff_agenda_items').insert(submission_data).execute()
                
                if result.data:
                    st.success("✅ Your agenda item has been submitted!")
                    st.info("It will appear in the next staff meeting agenda.")
                    st.balloons()
                    # Clear the form
                    st.rerun()
            
            except Exception as e:
                st.error(f"⚠️ Could not submit agenda item: {e}")
        else:
            st.warning("Please enter an agenda item before submitting.")

with col2:
    st.subheader("ℹ️ How It Works")
    st.write("""
    **1. Enter your item**  
    Type what you'd like discussed
    
    **2. Submit**  
    Click the submit button
    
    **3. Automatic inclusion**  
    Your item will appear in the next staff meeting agenda
    
    **Note:** Week/term are optional but help organize items
    """)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# VIEW PENDING ITEMS
# ══════════════════════════════════════════════════════════════════════════════

st.subheader("📋 Pending Agenda Items (All Staff)")

try:
    pending_result = supabase.table('staff_agenda_items').select('*').eq('status', 'pending').order('created_at', desc=True).execute()
    
    if pending_result.data:
        st.write(f"**{len(pending_result.data)} pending item(s)**")
        
        for item in pending_result.data:
            with st.expander(f"📌 {item['item_text'][:60]}..." if len(item['item_text']) > 60 else f"📌 {item['item_text']}"):
                st.write(f"**Submitted by:** {item['submitted_by']}")
                st.write(f"**Date:** {item['date_submitted']}")
                if item.get('week_number'):
                    st.write(f"**Week:** {item['week_number']}")
                if item.get('term'):
                    st.write(f"**Term:** {item['term']}")
                if item.get('category'):
                    st.write(f"**Category:** {item['category']}")
                st.markdown("---")
                st.write(f"**Item:** {item['item_text']}")
    else:
        st.info("No pending agenda items at the moment.")

except Exception as e:
    st.warning(f"Could not load pending items: {e}")

st.markdown("---")
st.caption("🏫 Cowandilla Learning Centre · LBU · Staff Agenda Submission")
