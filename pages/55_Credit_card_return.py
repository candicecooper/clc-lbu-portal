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

import io
import urllib.request
from zoneinfo import ZoneInfo

import streamlit as st
import pandas as pd
from datetime import date, datetime
from supabase import create_client
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

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

ADELAIDE_TZ = ZoneInfo("Australia/Adelaide")


def now_iso() -> str:
    """Current time in Adelaide, saved with its UTC offset so it's unambiguous."""
    return datetime.now(ADELAIDE_TZ).isoformat()


def format_dt(value) -> str:
    """Formats a stored timestamp for display in Adelaide time, human-readable
    (e.g. 31/08/2026 02:15 PM) instead of a raw ISO string or epoch number."""
    if not value:
        return ""
    try:
        dt = pd.to_datetime(value, utc=True).tz_convert(ADELAIDE_TZ)
        return dt.strftime("%d/%m/%Y %I:%M %p")
    except Exception:
        return str(value)


def format_date(value) -> str:
    """Formats a stored date for display as dd/mm/yyyy."""
    if not value:
        return ""
    try:
        return pd.to_datetime(value).strftime("%d/%m/%Y")
    except Exception:
        return str(value)

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


def fetch_open_requests(staff_member: str) -> pd.DataFrame:
    """Approved requests for this staff member that haven't been closed
    out by a return yet — these are the ones a return can link against."""
    res = (
        get_supabase()
        .table(REQUEST_TABLE)
        .select("*")
        .eq("staff_member", staff_member)
        .eq("status", REQ_APPROVED)
        .order("requested_at", desc=True)
        .execute()
    )
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()


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


def _fetch_bytes(url: str, timeout: int = 15) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read()


def build_return_form_pdf(row: dict) -> bytes:
    """Recreates the paper Form 2 layout as a PDF for one return, with the
    receipt image(s) shown underneath the details — used from the admin
    'View & Download' tab so a receipt can be sighted and filed without
    opening Supabase directly."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, height - 2 * cm, "Cowandilla Learning Centre")
    c.setFont("Helvetica", 13)
    c.drawString(2 * cm, height - 2.8 * cm, "Returning Credit Card — Form 2")

    y = height - 4 * cm
    fields = [
        ("Staff Member", row.get("staff_member", "")),
        ("Card(s)", ", ".join(row.get("card_names") or [])),
        ("Date on receipt", format_date(row.get("receipt_date"))),
        ("Total on receipt", f"${row.get('total_amount', 0):.2f}"),
        ("Notes", (row.get("notes") or "")[:90]),
        ("Status", row.get("status", "")),
        ("Submitted", format_dt(row.get("submitted_at"))),
        ("Admin approved by", row.get("admin_approved_by") or ""),
        ("Admin approved at", format_dt(row.get("admin_approved_at"))),
    ]
    for label, value in fields:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(2 * cm, y, f"{label}:")
        c.setFont("Helvetica", 10)
        c.drawString(6 * cm, y, str(value))
        y -= 0.7 * cm

    y -= 0.4 * cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2 * cm, y, "Attached receipt(s):")
    y -= 0.3 * cm

    urls = row.get("receipt_urls") or ([row["receipt_url"]] if row.get("receipt_url") else [])
    for url in urls:
        if not url:
            continue
        try:
            ext = url.split("?")[0].split(".")[-1].lower()
            if ext == "pdf":
                if y < 3 * cm:
                    c.showPage()
                    y = height - 2 * cm
                c.setFont("Helvetica-Oblique", 9)
                c.drawString(2 * cm, y, f"(Receipt attached as a PDF — see: {url[:75]})")
                y -= 1 * cm
                continue

            img_bytes = _fetch_bytes(url)
            img = ImageReader(io.BytesIO(img_bytes))
            iw, ih = img.getSize()
            max_w, max_h = width - 4 * cm, 13 * cm
            scale = min(max_w / iw, max_h / ih, 1)
            draw_w, draw_h = iw * scale, ih * scale
            if y - draw_h < 2 * cm:
                c.showPage()
                y = height - 2 * cm
            c.drawImage(img, 2 * cm, y - draw_h, width=draw_w, height=draw_h, preserveAspectRatio=True)
            y -= draw_h + 0.7 * cm
        except Exception as e:
            c.setFont("Helvetica-Oblique", 9)
            c.drawString(2 * cm, y, f"(Could not load this receipt: {e})")
            y -= 1 * cm

    c.save()
    buf.seek(0)
    return buf.getvalue()


# ---- page ---------------------------------------------------------------
st.set_page_config(page_title="Credit Card Request & Return", page_icon="💳", layout="wide")

# NOTE: staff login intentionally removed at Candice's request — anyone with
# the portal link can open Request/Return/Register. The Admin tab still
# requires the confidential/admin password via require_confidential_auth().

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
                    "requested_at": now_iso(),
                }
            )
            st.success(f"Request submitted for {req_staff} — awaiting admin approval.")

# ------------------------------------------------------------------ STEP 2
with tab_return:
    st.subheader("Return a card (Form 2)")
    st.write(
        "Select the approved request this return is closing out, attach a "
        "photo or screenshot of the receipt, and confirm — no need to "
        "print or staple anything."
    )

    ret_staff = st.selectbox("Staff Member", STAFF_LIST, key="ret_staff") if STAFF_LIST else None
    open_requests = fetch_open_requests(ret_staff) if ret_staff else pd.DataFrame()

    if ret_staff and open_requests.empty:
        st.info(f"No approved outstanding card requests for {ret_staff}. "
                "Submit a request first, or ask admin to approve one.")

    linked_request = None
    if not open_requests.empty:
        options = {
            row["id"]: f"{', '.join(row.get('card_names') or [])} — approx "
            f"${row['approx_cost']:.2f} — requested {format_date(row['requested_at'])}"
            for _, row in open_requests.iterrows()
        }
        picked_id = st.selectbox(
            "Which approved request is this returning?",
            options.keys(),
            format_func=lambda i: options[i],
            key="ret_request_id",
        )
        linked_request = open_requests[open_requests["id"] == picked_id].iloc[0]
        st.caption(f"Card(s): {', '.join(linked_request.get('card_names') or [])} — "
                   f"reason given: {linked_request.get('explanation', '')}")

    with st.form("submit_return_form", clear_on_submit=True):
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
        card_returned = st.checkbox("I am physically returning the card along with this receipt.")
        confirm = st.checkbox(
            "I confirm the above is accurate — this stands in place of my signature."
        )
        submitted = st.form_submit_button("Submit Return", type="primary")

    if submitted:
        if not ret_staff:
            st.error("Select a staff member.")
        elif linked_request is None:
            st.error("There's no approved request to link this return to.")
        elif total_amount <= 0:
            st.error("Enter the total on the receipt.")
        elif not receipt_files:
            st.error("Attach at least one receipt image/screenshot/PDF before submitting.")
        elif not card_returned:
            st.error("Tick to confirm the physical card is being returned.")
        elif not confirm:
            st.error("Tick the confirmation box to submit — this replaces the signature.")
        else:
            with st.spinner("Uploading receipt(s) and saving..."):
                receipt_urls = upload_receipts(receipt_files, ret_staff)
                insert_submission(
                    {
                        "staff_member": ret_staff,
                        "card_names": linked_request.get("card_names"),
                        "request_id": int(linked_request["id"]),
                        "receipt_date": receipt_date.isoformat(),
                        "total_amount": total_amount,
                        "notes": notes,
                        "receipt_url": receipt_urls[0] if receipt_urls else None,
                        "receipt_urls": receipt_urls,
                        "status": RET_PENDING,
                        "submitted_at": now_iso(),
                    }
                )
            st.success(f"Return submitted for {ret_staff} — awaiting admin sign-off.")

# ------------------------------------------------------------------ STEP 3
with tab_register:
    st.subheader("Full register")
    reg_view = st.radio("Show", ["Card Requests", "Card Returns"], horizontal=True)

    if reg_view == "Card Requests":
        status_filter = st.selectbox("Filter by status", ["All", REQ_PENDING, REQ_APPROVED, REQ_DECLINED, "Completed"])
        df = fetch_requests(None if status_filter == "All" else status_filter)
        cols = ["staff_member", "card_names", "approx_cost", "explanation", "status",
                "requested_at", "admin_approved_by", "admin_approved_at"]
        dt_cols, date_cols = ["requested_at", "admin_approved_at"], []
    else:
        status_filter = st.selectbox("Filter by status", ["All", RET_PENDING, RET_APPROVED, RET_RETURNED])
        df = fetch_submissions(None if status_filter == "All" else status_filter)
        cols = ["staff_member", "card_names", "receipt_date", "total_amount", "status",
                "submitted_at", "admin_approved_by", "admin_approved_at", "notes"]
        dt_cols, date_cols = ["submitted_at", "admin_approved_at"], ["receipt_date"]

    if df.empty:
        st.write("No records yet.")
    else:
        display_cols = [c for c in cols if c in df.columns]
        disp_df = df[display_cols].copy()
        if "card_names" in disp_df.columns:
            disp_df["card_names"] = disp_df["card_names"].apply(
                lambda v: ", ".join(v) if isinstance(v, list) else (v or "")
            )
        for c in dt_cols:
            if c in disp_df.columns:
                disp_df[c] = disp_df[c].apply(format_dt)
        for c in date_cols:
            if c in disp_df.columns:
                disp_df[c] = disp_df[c].apply(format_date)

        st.dataframe(disp_df, use_container_width=True, hide_index=True)
        csv = disp_df.to_csv(index=False).encode("utf-8")
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
        "Section",
        ["Approve Requests", "Approve Returns", "View & Download Forms", "Manage Staff & Cards"],
        horizontal=True,
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
                        st.caption(f"Requested {format_dt(row['requested_at'])}")
                        st.write(row.get("explanation", ""))
                    with c2:
                        if st.button("✅ Approve", key=f"req_approve_{row['id']}"):
                            update_request(row["id"], {
                                "status": REQ_APPROVED,
                                "admin_approved_by": st.session_state.get("admin_name", "Admin"),
                                "admin_approved_at": now_iso(),
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
                        st.caption(f"Receipt dated {format_date(row['receipt_date'])} · submitted {format_dt(row['submitted_at'])}")
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
                                "admin_approved_at": now_iso(),
                            })
                            if row.get("request_id"):
                                update_request(int(row["request_id"]), {"status": "Completed"})
                            st.rerun()
                        if st.button("↩️ Return for correction", key=f"ret_return_{row['id']}"):
                            update_submission(row["id"], {"status": RET_RETURNED})
                            st.rerun()

    elif admin_section == "View & Download Forms":
        dl_status = st.selectbox(
            "Filter by status", ["All", RET_PENDING, RET_APPROVED, RET_RETURNED], key="dl_filter"
        )
        dl_df = fetch_submissions(None if dl_status == "All" else dl_status)
        if dl_df.empty:
            st.write("No returns to show.")
        else:
            for _, row in dl_df.iterrows():
                with st.container(border=True):
                    cards = ", ".join(row.get("card_names") or [])
                    st.markdown(
                        f"**{row['staff_member']}** — {cards} — ${row['total_amount']:.2f} — *{row['status']}*"
                    )
                    st.caption(
                        f"Receipt dated {format_date(row.get('receipt_date'))} · "
                        f"submitted {format_dt(row.get('submitted_at'))}"
                    )
                    if row.get("notes"):
                        st.write(row["notes"])

                    pdf_key = f"pdf_bytes_{row['id']}"
                    gen_col, dl_col = st.columns([1, 1])
                    with gen_col:
                        if st.button("📄 Generate form", key=f"gen_{row['id']}"):
                            with st.spinner("Building form with receipt attached..."):
                                st.session_state[pdf_key] = build_return_form_pdf(row)
                    with dl_col:
                        if pdf_key in st.session_state:
                            st.download_button(
                                "⬇️ Download form (PDF)",
                                st.session_state[pdf_key],
                                file_name=(
                                    f"CreditCardReturn_{str(row['staff_member']).replace(' ', '_')}"
                                    f"_{row['id']}.pdf"
                                ),
                                mime="application/pdf",
                                key=f"dl_{row['id']}",
                            )

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
