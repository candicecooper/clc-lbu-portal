"""
Club Fees & Events — CLC-LBU Portal
-------------------------------------
Information sheet for Social Club: current fees, plus upcoming events.
Both sections have an editable, password-gated admin area.

WHAT THIS DOES
  - "Club Fees" tab: read-only list of current fees/items, for all staff to view.
  - "Upcoming Events" tab: read-only list of upcoming Social Club events —
        what it is, who to tell if you're attending, an optional RSVP
        cutoff date, and an optional cost.
  - "Admin" tab: password-gated. Two sub-sections:
        Manage Fees   — edit/add/delete fee items
        Manage Events — edit/add/delete events

SETUP NEEDED BEFORE THIS WILL RUN
  1. Supabase tables — run supabase_schema_club_fees.sql (if not already
     run) and supabase_schema_club_events.sql once each in the Supabase
     SQL editor.

  2. This file expects the same Supabase secrets your other tools use:
        st.secrets["SUPABASE_URL"]
        st.secrets["SUPABASE_KEY"]
     If your other pages import a shared client (e.g. from supabase_client.py),
     swap the init block below for that import instead — just keep the
     variable name `supabase`.

  3. Password gate: looks for STAFF_PASSWORD in Streamlit secrets first,
     then in a plain OS environment variable (covers both how Render's
     dashboard sets things and a secrets.toml approach).

  4. File is named 59_club_fees.py to match the existing repo. Tile link
     in the portal launcher (Social Club section) already points to
     /club_fees — no change needed there for this update.
"""

import os
import streamlit as st
from datetime import datetime, date
from supabase import create_client

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Club Fees & Events", page_icon="☕", layout="centered")

@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_supabase()

FEES_TABLE = "club_fees"
EVENTS_TABLE = "club_events"

FREQUENCY_OPTIONS = ["per term", "per year", "one-off", "per week", "other"]


def get_staff_password() -> str:
    """
    Look for the admin password in Streamlit secrets first, then fall back
    to a plain OS environment variable. Render's dashboard "Environment"
    tab sets the latter, not the former.
    """
    try:
        value = st.secrets.get("STAFF_PASSWORD")
        if value:
            return value
    except Exception:
        pass
    return os.environ.get("STAFF_PASSWORD", "")


def check_password() -> bool:
    """Lightweight staff-level password gate for the Admin tab."""
    if st.session_state.get("club_fees_admin_ok"):
        return True

    configured_password = get_staff_password()
    if not configured_password:
        st.warning(
            "No admin password is configured yet. Add a `STAFF_PASSWORD` "
            "value in Render (Environment tab) or in this app's Streamlit "
            "secrets, then redeploy/restart the service."
        )
    else:
        st.caption(f"Admin password is configured ({len(configured_password)} characters).")

    pwd = st.text_input("Admin password", type="password", key="club_fees_pwd_input")
    if st.button("Unlock admin section"):
        if configured_password and pwd == configured_password:
            st.session_state["club_fees_admin_ok"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


# ---------------------------------------------------------------------------
# Data access — every write is wrapped so a real failure shows up on screen
# instead of a false "Saved" message. Every write also re-queries afterward
# to confirm the row is actually there before declaring success.
# ---------------------------------------------------------------------------

def db_call(label: str, fn):
    """Run a Supabase call, surface any error, return the response or None."""
    try:
        return fn()
    except Exception as e:
        st.error(f"{label} failed: {e}")
        return None


def fetch_fees():
    res = db_call(
        "Loading fees",
        lambda: supabase.table(FEES_TABLE).select("*").order("display_order").order("id").execute(),
    )
    return res.data if res else []


def fetch_events(upcoming_only: bool = False):
    query = supabase.table(EVENTS_TABLE).select("*")
    if upcoming_only:
        query = query.gte("event_date", date.today().isoformat())
    res = db_call("Loading events", lambda: query.order("event_date").execute())
    return res.data if res else []


def seed_default_fees_if_empty():
    if fetch_fees():
        return
    defaults = [
        {"item_name": "Tea and Coffee", "amount": 10, "frequency": "per term", "notes": "", "display_order": 1},
        {"item_name": "Social Club", "amount": 30, "frequency": "per term", "notes": "", "display_order": 2},
    ]
    db_call("Seeding default fees", lambda: supabase.table(FEES_TABLE).insert(defaults).execute())


seed_default_fees_if_empty()

# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("☕ Club Fees & Events")
st.caption("Social Club — current fees and upcoming events")

tab_fees, tab_events, tab_admin = st.tabs(["Club Fees", "Upcoming Events", "Admin"])

# --- FEES VIEW TAB -----------------------------------------------------------
with tab_fees:
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

# --- EVENTS VIEW TAB ----------------------------------------------------------
with tab_events:
    events = fetch_events(upcoming_only=True)

    if not events:
        st.info("No upcoming events at the moment.")
    else:
        for ev in events:
            with st.container(border=True):
                ev_date = ev.get("event_date")
                try:
                    date_display = datetime.strptime(ev_date, "%Y-%m-%d").strftime("%A %d %B %Y")
                except Exception:
                    date_display = ev_date

                st.markdown(f"**{ev['title']}**")
                st.caption(date_display)

                if ev.get("info"):
                    st.write(ev["info"])

                details = []
                if ev.get("rsvp_contact"):
                    details.append(f"📋 Let **{ev['rsvp_contact']}** know if you're attending")
                if ev.get("rsvp_cutoff"):
                    try:
                        cutoff_display = datetime.strptime(ev["rsvp_cutoff"], "%Y-%m-%d").strftime("%A %d %B")
                    except Exception:
                        cutoff_display = ev["rsvp_cutoff"]
                    details.append(f"⏰ RSVP by **{cutoff_display}**")
                if ev.get("cost") not in (None, ""):
                    details.append(f"💲 **${float(ev['cost']):.0f}**")

                for d in details:
                    st.markdown(d)

    st.divider()
    st.caption("Events shown here are kept up to date by Social Club.")

# --- ADMIN TAB ----------------------------------------------------------------
with tab_admin:
    if not check_password():
        st.stop()

    st.success("Admin unlocked")
    if st.button("Lock admin section"):
        st.session_state["club_fees_admin_ok"] = False
        st.rerun()

    manage_fees_tab, manage_events_tab = st.tabs(["Manage Fees", "Manage Events"])

    # --- Manage Fees ---
    with manage_fees_tab:
        st.subheader("Edit existing items")
        fees = fetch_fees()
        st.caption(f"{len(fees)} fee item(s) currently in the database.")

        if not fees:
            st.info("Nothing to edit yet — add your first item below.")
        else:
            for fee in fees:
                with st.expander(f"{fee['item_name']} — ${fee['amount']:.0f} {fee['frequency']}"):
                    with st.form(f"edit_fee_form_{fee['id']}"):
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
                            res = db_call(
                                "Save",
                                lambda: supabase.table(FEES_TABLE).update({
                                    "item_name": name,
                                    "amount": amount,
                                    "frequency": frequency,
                                    "notes": notes,
                                    "display_order": order,
                                    "updated_at": datetime.utcnow().isoformat(),
                                }).eq("id", fee["id"]).execute(),
                            )
                            if res is not None:
                                st.success("Saved.")
                                st.rerun()

                        if delete:
                            res = db_call("Delete", lambda: supabase.table(FEES_TABLE).delete().eq("id", fee["id"]).execute())
                            if res is not None:
                                st.success("Deleted.")
                                st.rerun()

        st.divider()
        st.subheader("Add a new item")
        with st.form("add_fee_form", clear_on_submit=True):
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
                    insert_res = db_call(
                        "Add item",
                        lambda: supabase.table(FEES_TABLE).insert({
                            "item_name": new_name.strip(),
                            "amount": new_amount,
                            "frequency": new_frequency,
                            "notes": new_notes,
                            "display_order": existing_count + 1,
                        }).execute(),
                    )
                    # Confirm it actually landed before declaring success
                    if insert_res is not None:
                        confirm = db_call(
                            "Confirming add",
                            lambda: supabase.table(FEES_TABLE).select("id").eq("item_name", new_name.strip()).execute(),
                        )
                        if confirm and confirm.data:
                            st.success(f"Added {new_name} — confirmed in the database.")
                            st.rerun()
                        else:
                            st.error(
                                "The add request completed without an error, but the item "
                                "couldn't be found when checked straight afterwards. This "
                                "usually means the table's Row Level Security policies "
                                "don't match what supabase_schema_club_fees.sql sets up — "
                                "worth re-checking that in the Supabase SQL editor."
                            )

    # --- Manage Events ---
    with manage_events_tab:
        st.subheader("Edit existing events")
        events = fetch_events()
        st.caption(f"{len(events)} event(s) currently in the database.")

        if not events:
            st.info("Nothing to edit yet — add your first event below.")
        else:
            for ev in events:
                with st.expander(f"{ev['title']} — {ev['event_date']}"):
                    with st.form(f"edit_event_form_{ev['id']}"):
                        title = st.text_input("Event name", value=ev["title"])
                        try:
                            current_date = datetime.strptime(ev["event_date"], "%Y-%m-%d").date()
                        except Exception:
                            current_date = date.today()
                        event_date = st.date_input("Event date", value=current_date)
                        info = st.text_area("Info for staff", value=ev.get("info") or "")
                        rsvp_contact = st.text_input("Let this person know if attending", value=ev.get("rsvp_contact") or "")

                        has_cutoff = st.checkbox("Has an RSVP cutoff date", value=bool(ev.get("rsvp_cutoff")))
                        rsvp_cutoff = None
                        if has_cutoff:
                            try:
                                current_cutoff = datetime.strptime(ev["rsvp_cutoff"], "%Y-%m-%d").date()
                            except Exception:
                                current_cutoff = date.today()
                            rsvp_cutoff = st.date_input("RSVP by", value=current_cutoff, key=f"cutoff_{ev['id']}")

                        has_cost = st.checkbox("Has a cost", value=ev.get("cost") not in (None, ""))
                        cost = None
                        if has_cost:
                            cost = st.number_input(
                                "Cost ($)",
                                value=float(ev["cost"]) if ev.get("cost") not in (None, "") else 0.0,
                                min_value=0.0,
                                step=1.0,
                                key=f"cost_{ev['id']}",
                            )

                        c1, c2 = st.columns(2)
                        save = c1.form_submit_button("Save changes")
                        delete = c2.form_submit_button("Delete this event", type="secondary")

                        if save:
                            res = db_call(
                                "Save",
                                lambda: supabase.table(EVENTS_TABLE).update({
                                    "title": title,
                                    "event_date": event_date.isoformat(),
                                    "info": info,
                                    "rsvp_contact": rsvp_contact,
                                    "rsvp_cutoff": rsvp_cutoff.isoformat() if rsvp_cutoff else None,
                                    "cost": cost,
                                    "updated_at": datetime.utcnow().isoformat(),
                                }).eq("id", ev["id"]).execute(),
                            )
                            if res is not None:
                                st.success("Saved.")
                                st.rerun()

                        if delete:
                            res = db_call("Delete", lambda: supabase.table(EVENTS_TABLE).delete().eq("id", ev["id"]).execute())
                            if res is not None:
                                st.success("Deleted.")
                                st.rerun()

        st.divider()
        st.subheader("Add a new event")
        with st.form("add_event_form", clear_on_submit=True):
            new_title = st.text_input("Event name")
            new_date = st.date_input("Event date", value=date.today())
            new_info = st.text_area("Info for staff")
            new_rsvp_contact = st.text_input("Let this person know if attending")

            new_has_cutoff = st.checkbox("Has an RSVP cutoff date")
            new_cutoff = st.date_input("RSVP by", value=date.today(), key="new_cutoff") if new_has_cutoff else None

            new_has_cost = st.checkbox("Has a cost")
            new_cost = st.number_input("Cost ($)", min_value=0.0, step=1.0, key="new_cost") if new_has_cost else None

            add_event = st.form_submit_button("Add event")

            if add_event:
                if not new_title.strip():
                    st.error("Please give the event a name.")
                else:
                    insert_res = db_call(
                        "Add event",
                        lambda: supabase.table(EVENTS_TABLE).insert({
                            "title": new_title.strip(),
                            "event_date": new_date.isoformat(),
                            "info": new_info,
                            "rsvp_contact": new_rsvp_contact,
                            "rsvp_cutoff": new_cutoff.isoformat() if new_cutoff else None,
                            "cost": new_cost,
                        }).execute(),
                    )
                    if insert_res is not None:
                        confirm = db_call(
                            "Confirming add",
                            lambda: supabase.table(EVENTS_TABLE).select("id").eq("title", new_title.strip()).execute(),
                        )
                        if confirm and confirm.data:
                            st.success(f"Added {new_title} — confirmed in the database.")
                            st.rerun()
                        else:
                            st.error(
                                "The add request completed without an error, but the event "
                                "couldn't be found when checked straight afterwards — check "
                                "the Row Level Security policies on club_events in Supabase."
                            )
