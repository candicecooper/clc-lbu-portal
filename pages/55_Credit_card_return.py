"""
47_Credit_Card_Return.py
Electronic version of CLC-LBU "Form 2 – Returning Credit Card"

Multi-step workflow:
  Step 1 – Staff Member submits the return (replaces the paper form + stapled receipt)
  Step 2 – Admin reviews and approves (replaces the "Admin Approved" signature line)
  Step 3 – Register / history view of every submission, with status and export

Fits the existing portal conventions:
  - staff_auth.py gates the whole page (staff-level password)
  - confidential_auth.py gates the Admin Approval tab (admin-level password)
  - Supabase for the data table + Storage bucket for the receipt image/PDF
  - Numbered page file dropped straight into the Streamlit multipage app

NOTE ON NUMBERING: named this 47_ on the assumption 46_Staff_Reference.py is
the highest number currently in the repo. Rename the file to whatever the
next free number actually is before uploading.

NOTE ON AUTH: this imports check_staff_password()/check_confidential_password()
from your shared auth modules. If your actual function names differ, just
adjust the two import lines and the two call sites — everything else is
independent of that.
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime
from supabase import create_client

# ---- shared portal auth (adjust names if yours differ) ----------------
from staff_auth import check_staff_password
try:
    from confidential_auth import check_confidential_password
except ImportError:
    # fallback so the page still runs if the confidential module isn't
    # present in this checkout — swap for your real import
    def check_confidential_password():
        return st.text_input("Admin password", type="password") == st.secrets.get(
            "CONFIDENTIAL_PASSWORD", ""
        )

# ---- config -------------------------------------------------------------
TABLE_NAME = "credit_card_returns"
BUCKET_NAME = "credit-card-receipts"

# Edit this list to match who actually holds a CLC credit card.
STAFF_LIST = [
    "Ben Selga",
    "Ben Sutton",
    "Brenton",
    "Caitie",
    "Cheryl",
    "Jacqui",
    "Naomi",
    "Susan Furga",
    "Vinnie",
    "Louise",
    "Other (type below)",
]

STATUS_PENDING = "Pending"
STATUS_APPROVED = "Approved"
STATUS_RETURNED = "Needs Correction"


@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


def upload_receipts(files, staff_name: str) -> list[str]:
    """Uploads one or more receipt files (photos, screenshots, PDFs) to
    Supabase Storage and returns their public URLs."""
    if not files:
        return []
    sb = get_supabase()
    safe_name = staff_name.replace(" ", "_")
    urls = []
    for i, file in enumerate(files):
        ext = file.name.split(".")[-1]
        path = (
            f"{safe_name}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}.{ext}"
        )
        sb.storage.from_(BUCKET_NAME).upload(
            path, file.getvalue(), {"content-type": file.type}
        )
        urls.append(sb.storage.from_(BUCKET_NAME).get_public_url(path))
    return urls


def insert_submission(record: dict):
    get_supabase().table(TABLE_NAME).insert(record).execute()


def fetch_submissions(status: str | None = None) -> pd.DataFrame:
    q = get_supabase().table(TABLE_NAME).select("*").order("submitted_at", desc=True)
    if status:
        q = q.eq("status", status)
    res = q.execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()


def update_submission(row_id, updates: dict):
    get_supabase().table(TABLE_NAME).update(updates).eq("id", row_id).execute()


# ---- page ---------------------------------------------------------------
st.set_page_config(page_title="Credit Card Return", page_icon="💳", layout="wide")

if not check_staff_password():
    st.stop()

st.title("💳 Credit Card Return")
st.caption("Electronic version of Form 2 — Returning Credit Card")

tab_submit, tab_admin, tab_register = st.tabs(
    ["1️⃣ Submit Return", "2️⃣ Admin Approval", "📋 Register / History"]
)

# ------------------------------------------------------------------ STEP 1
with tab_submit:
    st.subheader("Staff submission")
    st.write(
        "Fill this in when you return a CLC credit card, and attach a photo "
        "or PDF of the receipt — no need to print or staple anything."
    )

    with st.form("submit_return_form", clear_on_submit=True):
        staff_choice = st.selectbox("Staff Member", STAFF_LIST)
        staff_other = ""
        if staff_choice == "Other (type below)":
            staff_other = st.text_input("Enter staff member name")

        receipt_date = st.date_input("Date on receipt", value=date.today())
        total_amount = st.number_input(
            "Total on receipt ($)", min_value=0.0, step=0.01, format="%.2f"
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
        final_name = staff_other.strip() if staff_choice == "Other (type below)" else staff_choice
        if not final_name:
            st.error("Enter a staff member name.")
        elif total_amount <= 0:
            st.error("Enter the total on the receipt.")
        elif not receipt_files:
            st.error("Attach at least one receipt image/screenshot/PDF before submitting.")
        elif not confirm:
            st.error("Tick the confirmation box to submit — this replaces the signature.")
        else:
            with st.spinner("Uploading receipt(s) and saving..."):
                receipt_urls = upload_receipts(receipt_files, final_name)
                insert_submission(
                    {
                        "staff_member": final_name,
                        "receipt_date": receipt_date.isoformat(),
                        "total_amount": total_amount,
                        "notes": notes,
                        "receipt_url": receipt_urls[0] if receipt_urls else None,
                        "receipt_urls": receipt_urls,
                        "status": STATUS_PENDING,
                        "submitted_at": datetime.now().isoformat(),
                    }
                )
            st.success(f"Submitted for {final_name} — awaiting admin approval.")

# ------------------------------------------------------------------ STEP 2
with tab_admin:
    st.subheader("Admin approval")
    if not check_confidential_password():
        st.info("Admin password required to review and approve returns.")
        st.stop()

    pending_df = fetch_submissions(STATUS_PENDING)
    if pending_df.empty:
        st.success("No returns waiting on approval.")
    else:
        for _, row in pending_df.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**{row['staff_member']}** — ${row['total_amount']:.2f}")
                    st.caption(f"Receipt dated {row['receipt_date']} · submitted {row['submitted_at'][:16]}")
                    if row.get("notes"):
                        st.write(row["notes"])
                    urls = row.get("receipt_urls") or (
                        [row["receipt_url"]] if row.get("receipt_url") else []
                    )
                    for i, url in enumerate(urls, start=1):
                        label = "View receipt" if len(urls) == 1 else f"View receipt {i}"
                        st.markdown(f"[{label}]({url})")
                with c2:
                    if st.button("✅ Approve", key=f"approve_{row['id']}"):
                        update_submission(
                            row["id"],
                            {
                                "status": STATUS_APPROVED,
                                "admin_approved_by": st.session_state.get("admin_name", "Admin"),
                                "admin_approved_at": datetime.now().isoformat(),
                            },
                        )
                        st.rerun()
                    if st.button("↩️ Return for correction", key=f"return_{row['id']}"):
                        update_submission(row["id"], {"status": STATUS_RETURNED})
                        st.rerun()

# ------------------------------------------------------------------ STEP 3
with tab_register:
    st.subheader("Full register")
    status_filter = st.selectbox(
        "Filter by status", ["All", STATUS_PENDING, STATUS_APPROVED, STATUS_RETURNED]
    )
    df = fetch_submissions(None if status_filter == "All" else status_filter)

    if df.empty:
        st.write("No submissions yet.")
    else:
        display_cols = [
            c
            for c in [
                "staff_member",
                "receipt_date",
                "total_amount",
                "status",
                "submitted_at",
                "admin_approved_by",
                "admin_approved_at",
                "notes",
            ]
            if c in df.columns
        ]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

        csv = df[display_cols].to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download as CSV",
            csv,
            file_name=f"credit_card_returns_{date.today().isoformat()}.csv",
            mime="text/csv",
        )
