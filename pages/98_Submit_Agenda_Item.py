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
# Operational DB — stores staff_agenda_items
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
SUPABASE_SERVICE_KEY = st.secrets.get("SUPABASE_SERVICE_KEY", SUPABASE_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Meetings DB — stores staff_meetings (auto-create upcoming meeting)
SUPABASE_URL_MEETINGS = st.secrets.get("SUPABASE_URL_MEETINGS", SUPABASE_URL)
SUPABASE_KEY_MEETINGS = st.secrets.get("SUPABASE_SERVICE_KEY_MEETINGS",
                         st.secrets.get("SUPABASE_KEY_MEETINGS", SUPABASE_KEY))
supabase_mtg = create_client(SUPABASE_URL_MEETINGS, SUPABASE_KEY_MEETINGS)

# ── SA term/week helpers ──────────────────────────────────────────────────────
import re as _re

_TERM_STARTS_2026 = {
    "T1": datetime.date(2026, 1, 27),
    "T2": datetime.date(2026, 4, 27),
    "T3": datetime.date(2026, 7, 20),
    "T4": datetime.date(2026, 10, 12),
}
_TERM_ENDS_2026 = {
    "T1": datetime.date(2026, 4, 11),
    "T2": datetime.date(2026, 7, 4),
    "T3": datetime.date(2026, 9, 26),
    "T4": datetime.date(2026, 12, 12),
}

def _get_upcoming_term_week():
    """Return (term_short, week_num, meeting_date) for the next school Monday."""
    today = datetime.date.today()
    # Find next Monday (or today if it's Monday)
    days_ahead = (7 - today.weekday()) % 7
    next_monday = today + datetime.timedelta(days=days_ahead if days_ahead else 7)
    for term, start in _TERM_STARTS_2026.items():
        end = _TERM_ENDS_2026[term]
        if start <= next_monday <= end:
            week_num = (next_monday - start).days // 7 + 1
            return term, max(1, week_num), next_monday
    # Fallback — closest term
    for term, start in _TERM_STARTS_2026.items():
        if next_monday < start:
            return term, 1, start
    return "T4", 1, next_monday

def _ensure_staff_meeting(term: str, week_num: int, meeting_date: datetime.date):
    """Create a staff meeting record if one doesn't exist for this term/week."""
    import json
    try:
        existing = (supabase_mtg.table('staff_meetings')
                    .select('id')
                    .eq('term', term)
                    .eq('week_number', week_num)
                    .execute())
        if existing.data:
            return existing.data[0]['id'], False   # already exists
        # Create a skeleton meeting
        result = supabase_mtg.table('staff_meetings').insert({
            "meeting_date": str(meeting_date),
            "term": term,
            "week_number": week_num,
            "minute_taker": "",
            "attendees": "",
            "apologies": "",
            "agenda_items": json.dumps({"additional_agenda": []}),
            "minutes": "",
            "actions": "[]",
        }).execute()
        if result.data:
            return result.data[0]['id'], True   # newly created
    except Exception as e:
        return None, False

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
        term = st.selectbox("Term", options=["Auto-detect", "T1", "T2", "T3", "T4"],
                            index=0, key="term",
                            help="Leave as Auto-detect to target the upcoming school week")
        term = "" if term == "Auto-detect" else term
    with col_b:
        week_number = st.number_input("Week Number (0 = auto)", min_value=0, max_value=11,
                                      value=0, key="week",
                                      help="Leave as 0 to auto-detect the upcoming week")
    
    category = st.selectbox(
        "Category (optional)",
        options=["", "WHS", "Finance", "Social Club", "Policy", "Curriculum", "Other"],
        key="category"
    )
    
    if st.button("📤 Submit Agenda Item", type="primary", use_container_width=True):
        if agenda_item.strip():
            try:
                import json

                # ── Work out which meeting this belongs to ────────────────────
                # Use user-supplied term/week if provided, otherwise auto-detect
                if term.strip() and week_number > 0:
                    raw = _re.search(r'(\d)', term.strip())
                    auto_term = f"T{raw.group(1)}" if raw else "T2"
                    auto_week = week_number
                    auto_date = _TERM_STARTS_2026.get(auto_term, datetime.date.today()) + \
                                datetime.timedelta(weeks=auto_week - 1)
                else:
                    auto_term, auto_week, auto_date = _get_upcoming_term_week()

                # ── Submit the agenda item to operational DB ──────────────────
                submission_data = {
                    "submitted_by": staff_name,
                    "item_text": agenda_item.strip(),
                    "date_submitted": str(datetime.date.today()),
                    "week_number": auto_week,
                    "term": auto_term,
                    "status": "pending",
                    "category": category if category else None
                }
                result = supabase.table('staff_agenda_items').insert(submission_data).execute()

                if result.data:
                    item_id = result.data[0]['id']

                    # ── Ensure the staff meeting exists, create if not ─────────
                    meeting_id, was_created = _ensure_staff_meeting(auto_term, auto_week, auto_date)

                    if meeting_id:
                        # Load current agenda_items for this meeting
                        mtg = supabase_mtg.table('staff_meetings').select('agenda_items') \
                                          .eq('id', meeting_id).execute()
                        raw_agenda = mtg.data[0].get('agenda_items', '{}') if mtg.data else '{}'
                        try:
                            agenda = json.loads(raw_agenda) if isinstance(raw_agenda, str) else raw_agenda
                        except Exception:
                            agenda = {}
                        additional = agenda.get('additional_agenda', [])

                        # Add this item if not already there
                        item_label = f"{agenda_item.strip()} (submitted by {staff_name})"
                        if item_label not in additional:
                            additional.append(item_label)
                        agenda['additional_agenda'] = additional

                        # Save agenda back to meeting record
                        supabase_mtg.table('staff_meetings').update({
                            "agenda_items": json.dumps(agenda)
                        }).eq('id', meeting_id).execute()
                        # Leave status as 'pending' — Staff Meetings Load button handles marking as added

                        if was_created:
                            st.success(f"✅ Submitted! A new staff meeting has been created for {auto_term} Week {auto_week} ({auto_date}).")
                        else:
                            st.success(f"✅ Submitted and added to the {auto_term} Week {auto_week} staff meeting.")
                    else:
                        st.success("✅ Agenda item submitted! It will be loaded into the meeting manually.")

                    st.balloons()
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

st.subheader("📋 Submitted Agenda Items")

try:
    all_result = supabase.table('staff_agenda_items').select('*') \
                         .in_('status', ['pending', 'added']) \
                         .order('created_at', desc=True).execute()

    if all_result.data:
        pending_items = [i for i in all_result.data if i['status'] == 'pending']
        added_items   = [i for i in all_result.data if i['status'] == 'added']

        if pending_items:
            st.markdown(f"**⏳ Awaiting meeting — {len(pending_items)} item(s)**")
            for item in pending_items:
                label = item['item_text'][:60] + '…' if len(item['item_text']) > 60 else item['item_text']
                with st.expander(f"📌 {label}"):
                    st.write(f"**Submitted by:** {item['submitted_by']}")
                    st.write(f"**Date:** {item['date_submitted']}")
                    if item.get('term'): st.write(f"**Term/Week:** {item['term']} Wk {item.get('week_number','?')}")
                    if item.get('category'): st.write(f"**Category:** {item['category']}")
                    st.write(f"**Item:** {item['item_text']}")

        if added_items:
            st.markdown(f"**✅ Added to meeting — {len(added_items)} item(s)**")
            for item in added_items[:5]:   # show last 5 only
                label = item['item_text'][:60] + '…' if len(item['item_text']) > 60 else item['item_text']
                with st.expander(f"✅ {label}", expanded=False):
                    st.write(f"**Submitted by:** {item['submitted_by']}")
                    if item.get('term'): st.write(f"**Term/Week:** {item['term']} Wk {item.get('week_number','?')}")
                    st.write(f"**Item:** {item['item_text']}")

        if not pending_items and not added_items:
            st.info("No agenda items submitted yet.")
    else:
        st.info("No agenda items submitted yet.")

except Exception as e:
    st.warning(f"Could not load items: {e}")

st.markdown("---")
st.caption("🏫 Cowandilla Learning Centre · LBU · Staff Agenda Submission")
