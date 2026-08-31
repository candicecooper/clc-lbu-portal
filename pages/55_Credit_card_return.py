"""
55_Credit_card_return.py
Electronic version of CLC-LBU Form 1 (Requesting Credit Card) and
Form 2 (Returning Credit Card), combined into one staff/admin workflow.

Workflow:
  Step 1 - Request card (Form 1): staff requests a card, gives an
           approximate cost and a reason; admin approves or declines
  Step 2 - Return card (Form 2): staff returns the card with a receipt;
           admin approves or sends back for correction
  Step 3 - Register: full history of requests and returns
  Step 4 - Admin (password-gated): approve requests, approve returns, and
           manage the staff / card name lists used as options elsewhere
           on the page

NOTE ON AUTH: uses require_staff_auth() from staff_auth.py and
require_confidential_auth() from confidential_auth.py, matching the real
signatures used elsewhere in the portal. If confidential_auth.py's
function name or signature differs, only the import block below needs
adjusting.

NOTE ON TAB ORDER: require_confidential_auth() calls st.stop() when
locked, and Streamlit executes every "with tab:" block on each script run
regardless of which tab is currently showing. So the single Admin tab's
code is placed LAST in the source (even though it displays as the last
tab already) - this way Request / Return / Register always render even
before anyone has entered the admin password.
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime
from supabase import create_client

from staff_auth import require_staff_auth
try:
    from confidential_auth import require_confidential_auth
except ImportError:
    def require_confidential_auth(title="Admin", icon="🔒", subtitle=""):
        if st.session_state.get("_cc_admin_ok"):
            return True
        pwd = st.text_input("Admin password", type="password", key="_cc_admin_pwd")
        if pwd and pwd == st.secrets.get("CONFIDENTIAL_PASSWORD", ""):
            st.session_state["_cc_admin_ok"] = True
            st.rerun()
        st.stop()
        return False

# ---- config -------------------------------------------------------------
REQUEST_TABLE = "credit_card_requests"
RETURN_TABLE = "credit_card_returns"
STAFF_TABLE = "cc_staff"
CARD_TABLE = "cc_cards"
BUCKET_NAME = "credit-card-receipts"

REQ_PENDING, REQ_APPROVED, REQ_DECLINED = "Pending", "Approved", "Declined"
RET_PENDING, RET_APPROVED, RET_RETURNED = "Pending", "Approved", "Needs Correction"


@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


# ---- staff & card lookup lists (admin-editable, stored in Supabase) -----
def fetch_names(table: str) -> list[str]:
    res = get_supabase().table(table).select("name").order("name").execute()
    return [r["name"] for r in res.data] if res.data else []


def add_name(table: str, name: str):
    name = name.strip()
    if not name:
        return
    get_supabase().table(table).insert({"name": name}).execute()


def delete_name(table: str, name: str):
    get_supabase().table(table).delete().eq("name", name).execute()


# ---- receipts (Supabase Storage) -----------------------------------------
def upload_receipts(files, staff_name: str) -> list[str]:
    if not files:
        return []
    sb = get_supabase()
    safe_name = staff_name.replace(" ", "_")
    urls = []
    for i, file in enumerate(files):
        ext = file.name.split(".")[-1]
        path = f"{safe_name}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}.{ext}"
        sb.storage.from_(BUCKET_NAME).upload(path, file.getvalue(), {"content-type": file.type})
        urls.append(sb.storage.from_(BUCKET_NAME).get_public_url(path))
    return urls


# ---- requests (Form 1) ----------------------------------------------------
def insert_request(record: dict):
    get_supabase().table(REQUEST_TABLE).insert(record).execute()


def fetch_requests(status: str | None = None) -> pd.DataFrame:
    q = get_supabase().table(REQUEST_TABLE).select("*").order("requested_at", desc=True)
    if status:
        q = q.eq("status", status)
    res = q.execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()


def update_request(row_id, updates: dict):
    get_supabase().table(REQUEST_TABLE).update(updates).eq("id", row_id).execute()


# ---- returns (Form 2) ------------------------------------------------------
def insert_submission(record: dict):
    get_supabase().table(RETURN_TABLE).insert(record).execute()


def fetch_submissions(status: str | None = None) -> pd.DataFrame:
    q = get_supabase().table(RETURN_TABLE).select("*").order("submitted_at", desc=True)
    if status:
        q = q.eq("status", status)
    res = q.execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()


def update_submission(row_id, updates: dict):
    get_supabase().table(RETURN_TABLE).update(updates).eq("id", row_id).execute()


def card_tickboxes(card_list: list[str], key_prefix: str) -> list[str]:
    """Renders one checkbox per card name and returns the ticked ones."""
    picked = []
    cols = st.columns(len(card_list)) if card_list else []
    for col, card in zip(cols, card_list):
        with col:
            if st.checkbox(card, key=f"{key_prefix}_{card}"):
                picked.append(card)
    return picked


# ---- page ---------------------------------------------------------------
st.set_page_config(page_title="Credit Card Request & Return", page_icon="💳", layout="wide")

require_staff_auth("Credit Card Request & Return", "💳", "Cowandilla Learning Centre — LBU Staff")

st.title("💳 Credit Card Request & Return")
st.caption("Electronic Form 1 (Requesting) and Form 2 (Returning)")

STAFF_LIST = fetch_names(STAFF_TABLE)
CARD_LIST = fetch_names(CARD_TABLE)

tab_request, tab_return, tab_register, tab_admin = st.tabs(
    ["1️⃣ Request Card", "2️⃣ Return Card", "📋 Register", "🔒 Admin"]
)

# ------------------------------------------------------------------ STEP 1
with tab_request:
    st.subheader("Request a card (Form 1)")
    st.write("Fill this in before taking a CLC credit card, so admin can approve it up front.")

    with st.form("request_card_form", clear_on_submit=True):
        req_staff = st.selectbox("Staff Member", STAFF_LIST, key="req_staff") if STAFF_LIST else None
        if not STAFF_LIST:
            st.warning("No staff members set up yet — add some in the Admin tab first.")

        st.write("Which card?")
        req_cards = card_tickboxes(CARD_LIST, "req_card")
        if not CARD_LIST:
            st.warning("No cards set up yet — add some in the Admin tab first.")

        req_cost = st.number_input("Approximate cost ($)", min_value=0.0, step=0.01, format="%.2f")
        req_reason = st.text_area("Explanation", placeholder="What's this for?")
        req_submitted = st.form_submit_button("Submit Request", type="primary")

    if req_submitted:
        if not req_staff:
            st.error("Select a staff member.")
        elif not req_cards:
            st.error("Tick at least one card.")
        elif req_cost <= 0:
            st.error("Enter the approximate cost.")
        elif not req_reason.strip():
            st.error("Enter an explanation for the request.")
        else:
            insert_request(
                {
                    "staff_member": req_staff,
                    "card_names": req_cards,
                    "approx_cost": req_cost,
                    "explanation": req_reason.strip(),
                    "status": REQ_PENDING,
                    "requested_at": datetime.now().isoformat(),
                }
            )
            st.success(f"Request submitted for {req_staff} — awaiting admin approval.")

# ------------------------------------------------------------------ STEP 2
with tab_return:
    st.subheader("Return a card (Form 2)")
    st.write(
        "Fill this in when you return a CLC credit card, and attach a photo "
        "or screenshot of the receipt — no need to print or staple anything."
    )

    with st.form("submit_return_form", clear_on_submit=True):
        ret_staff = st.selectbox("Staff Member", STAFF_LIST, key="ret_staff") if STAFF_LIST else None

        st.write("Which card are you returning?")
        ret_cards = card_tickboxes(CARD_LIST, "ret_card")

        receipt_date = st.date_input("Date on receipt", value=date.today())
        total_amount = st.number_input(
            "Total on receipt ($)", min_value=0.0, step=0.01, format="%.2f", key="ret_total"
        )
        receipt_files = st.file_uploader(
            "Attach receipt (photo, screenshot, or PDF — you can add more than one, "
            "e.g. an order confirmation screenshot plus a photo of the paper receipt)",
            type=["png", "jpg", "jpeg", "pdf"],
            accept_multiple_files=True,
        )
        notes = st.text_area("Notes (optional)", placeholder="What was purchased, cost centre, etc.")
        confirm = st.checkbox(
            "I confirm the above is accurate — this stands in place of my signature."
        )
        submitted = st.form_submit_button("Submit Return", type="primary")

    if submitted:
        if not ret_staff:
            st.error("Select a staff member.")
        elif not ret_cards:
            st.error("Tick which card is being returned.")
        elif total_amount <= 0:
            st.error("Enter the total on the receipt.")
        elif not receipt_files:
            st.error("Attach at least one receipt image/screenshot/PDF before submitting.")
        elif not confirm:
            st.error("Tick the confirmation box to submit — this replaces the signature.")
        else:
            with st.spinner("Uploading receipt(s) and saving..."):
                receipt_urls = upload_receipts(receipt_files, ret_staff)
                insert_submission(
                    {
                        "staff_member": ret_staff,
                        "card_names": ret_cards,
                        "receipt_date": receipt_date.isoformat(),
                        "total_amount": total_amount,
                        "notes": notes,
                        "receipt_url": receipt_urls[0] if receipt_urls else None,
                        "receipt_urls": receipt_urls,
                        "status": RET_PENDING,
                        "submitted_at": datetime.now().isoformat(),
                    }
                )
            st.success(f"Return submitted for {ret_staff} — awaiting admin approval.")

# ------------------------------------------------------------------ STEP 3
with tab_register:
    st.subheader("Full register")
    reg_view = st.radio("Show", ["Card Requests", "Card Returns"], horizontal=True)

    if reg_view == "Card Requests":
        status_filter = st.selectbox("Filter by status", ["All", REQ_PENDING, REQ_APPROVED, REQ_DECLINED])
        df = fetch_requests(None if status_filter == "All" else status_filter)
        cols = ["staff_member", "card_names", "approx_cost", "explanation", "status",
                "requested_at", "admin_approved_by", "admin_approved_at"]
    else:
        status_filter = st.selectbox("Filter by status", ["All", RET_PENDING, RET_APPROVED, RET_RETURNED])
        df = fetch_submissions(None if status_filter == "All" else status_filter)
        cols = ["staff_member", "card_names", "receipt_date", "total_amount", "status",
                "submitted_at", "admin_approved_by", "admin_approved_at", "notes"]

    if df.empty:
        st.write("No records yet.")
    else:
        display_cols = [c for c in cols if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
        csv = df[display_cols].to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download as CSV",
            csv,
            file_name=f"{reg_view.lower().replace(' ', '_')}_{date.today().isoformat()}.csv",
            mime="text/csv",
        )

# ------------------------------------------------------------------ STEP 4
with tab_admin:
    st.subheader("Admin")
    require_confidential_auth("Credit Card Request & Return — Admin", "🔒", "")

    admin_section = st.radio(
        "Section", ["Approve Requests", "Approve Returns", "Manage Staff & Cards"], horizontal=True
    )

    if admin_section == "Approve Requests":
        pending = fetch_requests(REQ_PENDING)
        if pending.empty:
            st.success("No requests waiting on approval.")
        else:
            for _, row in pending.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        cards = ", ".join(row.get("card_names") or [])
                        st.markdown(f"**{row['staff_member']}** — {cards} — approx ${row['approx_cost']:.2f}")
                        st.caption(f"Requested {row['requested_at'][:16]}")
                        st.write(row.get("explanation", ""))
                    with c2:
                        if st.button("✅ Approve", key=f"req_approve_{row['id']}"):
                            update_request(row["id"], {
                                "status": REQ_APPROVED,
                                "admin_approved_by": st.session_state.get("admin_name", "Admin"),
                                "admin_approved_at": datetime.now().isoformat(),
                            })
                            st.rerun()
                        if st.button("❌ Decline", key=f"req_decline_{row['id']}"):
                            update_request(row["id"], {"status": REQ_DECLINED})
                            st.rerun()

    elif admin_section == "Approve Returns":
        pending_df = fetch_submissions(RET_PENDING)
        if pending_df.empty:
            st.success("No returns waiting on approval.")
        else:
            for _, row in pending_df.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        cards = ", ".join(row.get("card_names") or [])
                        st.markdown(f"**{row['staff_member']}** — {cards} — ${row['total_amount']:.2f}")
                        st.caption(f"Receipt dated {row['receipt_date']} · submitted {row['submitted_at'][:16]}")
                        if row.get("notes"):
                            st.write(row["notes"])
                        urls = row.get("receipt_urls") or ([row["receipt_url"]] if row.get("receipt_url") else [])
                        for i, url in enumerate(urls, start=1):
                            label = "View receipt" if len(urls) == 1 else f"View receipt {i}"
                            st.markdown(f"[{label}]({url})")
                    with c2:
                        if st.button("✅ Approve", key=f"ret_approve_{row['id']}"):
                            update_submission(row["id"], {
                                "status": RET_APPROVED,
                                "admin_approved_by": st.session_state.get("admin_name", "Admin"),
                                "admin_approved_at": datetime.now().isoformat(),
                            })
                            st.rerun()
                        if st.button("↩️ Return for correction", key=f"ret_return_{row['id']}"):
                            update_submission(row["id"], {"status": RET_RETURNED})
                            st.rerun()

    else:  # Manage Staff & Cards
        m1, m2 = st.columns(2)
        with m1:
            st.markdown("**Staff members**")
            for name in STAFF_LIST:
                sc1, sc2 = st.columns([4, 1])
                sc1.write(name)
                if sc2.button("🗑️", key=f"del_staff_{name}"):
                    delete_name(STAFF_TABLE, name)
                    st.rerun()
            new_staff = st.text_input("Add staff member", key="new_staff_name")
            if st.button("➕ Add staff member") and new_staff.strip():
                add_name(STAFF_TABLE, new_staff)
                st.rerun()

        with m2:
            st.markdown("**Credit cards**")
            for name in CARD_LIST:
                cc1, cc2 = st.columns([4, 1])
                cc1.write(name)
                if cc2.button("🗑️", key=f"del_card_{name}"):
                    delete_name(CARD_TABLE, name)
                    st.rerun()
            new_card = st.text_input("Add card (e.g. \"Susan's\")", key="new_card_name")
            if st.button("➕ Add card") and new_card.strip():
                add_name(CARD_TABLE, new_card)
                st.rerun()
