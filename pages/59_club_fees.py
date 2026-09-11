"""
Club Fees — CLC-LBU Portal
---------------------------
Information sheet for Social Club, with an editable admin section.

WHAT THIS DOES
  - "Club Fees" tab: read-only list of current fees/items, for all staff to view.
  - "Admin" tab: password-gated. Lets Social Club / admin staff:
        - edit the amount, frequency, or notes on any existing item
        - add brand new fee items
        - delete an item that's no longer charged
        - re-order how items are displayed

SETUP NEEDED BEFORE THIS WILL RUN
  1. Supabase table (run once in the Supabase SQL editor):

        create table if not exists club_fees (
            id bigint generated always as identity primary key,
            item_name text not null,
            amount numeric not null,
            frequency text not null default 'per term',
            notes text default '',
            display_order int not null default 0,
            updated_at timestamptz not null default now(),
            updated_by text default ''
        );

  2. This file expects the same Supabase secrets your other tools use:
        st.secrets["SUPABASE_URL"]
        st.secrets["SUPABASE_KEY"]
     If your other pages import a shared client (e.g. from supabase_client.py),
     swap the init block below for that import instead — just keep the
     variable name `supabase`.

  3. Password gate: this file has its own lightweight password check using
        st.secrets["STAFF_PASSWORD"]
     so it works standalone. If you'd rather it use the shared staff_auth.py
     module like your other staff-level tools, replace the `check_password()`
     function with:
        from staff_auth import check_staff_password
     and call that instead — send me the function's exact name/signature and
     I'll wire it in to match exactly.

  4. Rename this file to whatever page number fits your sidebar ordering
     (it's currently `59_Club_Fees.py` as a placeholder).

  5. Point the existing "Club Fees" tile link (or add a new one) to this page.
"""

import streamlit as st
from datetime import datetime
from supabase import create_client

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Club Fees", page_icon="☕", layout="centered")

@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_supabase()

TABLE = "club_fees"

FREQUENCY_OPTIONS = ["per term", "per year", "one-off", "per week", "other"]


def check_password() -> bool:
    """Lightweight staff-level password gate for the Admin tab."""
    if st.session_state.get("club_fees_admin_ok"):
        return True

    pwd = st.text_input("Admin password", type="password", key="club_fees_pwd_input")
    if st.button("Unlock admin section"):
        if pwd == st.secrets.get("STAFF_PASSWORD", ""):
            st.session_state["club_fees_admin_ok"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


def fetch_fees():
    res = (
        supabase.table(TABLE)
        .select("*")
        .order("display_order")
        .order("id")
        .execute()
    )
    return res.data or []


def seed_default_fees_if_empty():
    existing = fetch_fees()
    if existing:
        return
    defaults = [
        {
            "item_name": "Tea and Coffee",
            "amount": 10,
            "frequency": "per term",
            "notes": "",
            "display_order": 1,
        },
        {
            "item_name": "Social Club",
            "amount": 30,
            "frequency": "per term",  # assumption — edit in Admin tab if this should be per year
            "notes": "",
            "display_order": 2,
        },
    ]
    supabase.table(TABLE).insert(defaults).execute()


seed_default_fees_if_empty()

# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("☕ Club Fees")
st.caption("Social Club — current fees and costs")

tab_view, tab_admin = st.tabs(["Club Fees", "Admin"])

# --- VIEW TAB ---------------------------------------------------------------
with tab_view:
    fees = fetch_fees()

    if not fees:
        st.info("No fees have been added yet.")
    else:
        for fee in fees:
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{fee['item_name']}**")
                    if fee.get("notes"):
                        st.caption(fee["notes"])
                with col2:
                    st.markdown(f"**${fee['amount']:.0f}**")
                    st.caption(fee["frequency"])

    st.divider()
    st.caption("Costs shown here are kept up to date by Social Club. If something looks wrong, flag it with Social Club or your Manager.")

# --- ADMIN TAB ----------------------------------------------------------------
with tab_admin:
    if not check_password():
        st.stop()

    st.success("Admin unlocked")
    if st.button("Lock admin section"):
        st.session_state["club_fees_admin_ok"] = False
        st.rerun()

    st.subheader("Edit existing items")
    fees = fetch_fees()

    if not fees:
        st.info("Nothing to edit yet — add your first item below.")
    else:
        for fee in fees:
            with st.expander(f"{fee['item_name']} — ${fee['amount']:.0f} {fee['frequency']}"):
                with st.form(f"edit_form_{fee['id']}"):
                    name = st.text_input("Item name", value=fee["item_name"])
                    amount = st.number_input("Amount ($)", value=float(fee["amount"]), min_value=0.0, step=1.0)
                    freq_index = FREQUENCY_OPTIONS.index(fee["frequency"]) if fee["frequency"] in FREQUENCY_OPTIONS else len(FREQUENCY_OPTIONS) - 1
                    frequency = st.selectbox("Frequency", FREQUENCY_OPTIONS, index=freq_index)
                    notes = st.text_area("Notes (optional)", value=fee.get("notes") or "")
                    order = st.number_input("Display order", value=int(fee.get("display_order") or 0), step=1)

                    c1, c2 = st.columns(2)
                    save = c1.form_submit_button("Save changes")
                    delete = c2.form_submit_button("Delete this item", type="secondary")

                    if save:
                        supabase.table(TABLE).update({
                            "item_name": name,
                            "amount": amount,
                            "frequency": frequency,
                            "notes": notes,
                            "display_order": order,
                            "updated_at": datetime.utcnow().isoformat(),
                        }).eq("id", fee["id"]).execute()
                        st.success("Saved.")
                        st.rerun()

                    if delete:
                        supabase.table(TABLE).delete().eq("id", fee["id"]).execute()
                        st.success("Deleted.")
                        st.rerun()

    st.divider()
    st.subheader("Add a new item")
    with st.form("add_form", clear_on_submit=True):
        new_name = st.text_input("Item name")
        new_amount = st.number_input("Amount ($)", min_value=0.0, step=1.0)
        new_frequency = st.selectbox("Frequency", FREQUENCY_OPTIONS)
        new_notes = st.text_area("Notes (optional)")
        add = st.form_submit_button("Add item")

        if add:
            if not new_name.strip():
                st.error("Please give the item a name.")
            else:
                existing_count = len(fetch_fees())
                supabase.table(TABLE).insert({
                    "item_name": new_name.strip(),
                    "amount": new_amount,
                    "frequency": new_frequency,
                    "notes": new_notes,
                    "display_order": existing_count + 1,
                }).execute()
                st.success(f"Added {new_name}.")
                st.rerun()
