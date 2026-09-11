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

NOTE ON AUTH: staff login was intentionally removed (see below) — anyone
with the portal link can open Request/Return/Register. Only the Admin tab
is gated, via require_confidential_auth() from confidential_auth.py.

NOTE ON TAB ORDER: require_confidential_auth() calls st.stop() when
locked, and Streamlit executes every "with tab:" block on each script run
regardless of which tab is currently showing. So the single Admin tab's
code is placed LAST in the source (even though it displays as the last
tab already) - this way Request / Return / Register always render even
before anyone has entered the admin password.
"""

import io
import smtplib
import urllib.request
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

import streamlit as st
import pandas as pd
from datetime import date, datetime
from supabase import create_client
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

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
FUNDING_TABLE = "additional_funding_requests"
SPEND_TABLE = "additional_funding_spend"
BUCKET_NAME = "credit-card-receipts"

REQ_PENDING, REQ_APPROVED, REQ_DECLINED = "Pending", "Approved", "Declined"
RET_PENDING, RET_APPROVED, RET_RETURNED = "Pending", "Approved", "Needs Correction"
BUDGET_OPTIONS = ["JP", "PY", "SY", "NIT", "ADMIN", "ADDITIONAL"]
PROGRAM_OPTIONS = ["JP", "PY", "SY", "NIT", "ADMIN"]
TERM_POOL = 500.0

# SA DfE public school term dates. TODO: add each new year here as it's
# published (education.sa.gov.au/teaching/term-dates) — this needs manual
# updating annually, same as the Trade Bookings tool's Term View.
SA_TERM_DATES = {
    2026: [
        (date(2026, 1, 27), date(2026, 4, 10)),
        (date(2026, 4, 27), date(2026, 7, 3)),
        (date(2026, 7, 20), date(2026, 9, 25)),
        (date(2026, 10, 12), date(2026, 12, 11)),
    ],
}


def get_term_for_date(d: date):
    """Returns (label, start, end) for the SA DfE term containing date d.
    Falls back to the closest year on file if d's year isn't mapped yet, and
    attributes holiday-period dates to whichever term just finished (or
    Term 1 if before the year's first term) — so the tracker always shows
    *a* term rather than breaking over a holiday break or a missing year."""
    year_terms = SA_TERM_DATES.get(d.year)
    if not year_terms:
        closest_year = min(SA_TERM_DATES.keys(), key=lambda y: abs(y - d.year))
        year_terms = SA_TERM_DATES[closest_year]
    for i, (start, end) in enumerate(year_terms, start=1):
        if start <= d <= end:
            return f"Term {i} {d.year}", start, end
    finished = [t for t in year_terms if t[1] < d]
    if finished:
        idx = year_terms.index(finished[-1]) + 1
        return f"Term {idx} {d.year}", finished[-1][0], finished[-1][1]
    return f"Term 1 {d.year}", year_terms[0][0], year_terms[0][1]


def get_current_term():
    return get_term_for_date(date.today())

# TODO Candice: confirm this is the right inbox for funding-request approvals —
# it's a guess based on your SharePoint personal-site URL, not confirmed.
# Used by the Additional Funding tab, where staff email their own completed
# PDF to the Manager — separate from the automatic alerts below.
MANAGER_EMAIL = "candice.cooper330@schools.sa.edu.au"

ALERT_EMAILS_TO = ["candice.cooper330@schools.sa.edu.au", "annette.balestrin13@schools.sa.edu.au"]


def send_alert_email(subject: str, body: str):
    """Best-effort email alert when a request/return is lodged. Reads SMTP
    creds from secrets — if they're not set up yet, this silently does
    nothing rather than blocking the staff member's submission.

    Needs these added under [secrets] in Render (Environment > Secrets
    Files, or Streamlit's secrets.toml):
        SMTP_HOST      (optional, defaults to smtp.gmail.com)
        SMTP_PORT      (optional, defaults to 587)
        SMTP_USER      the sending account's address (e.g. the existing
                       clc.digitalstaffmeeting@gmail.com)
        SMTP_PASSWORD  an app password for that account (not its normal
                       login password — Gmail: Google Account > Security >
                       2-Step Verification > App passwords)
        ALERT_EMAIL_TO (optional) comma-separated recipient override —
                       defaults to ALERT_EMAILS_TO above if not set
    """
    try:
        host = st.secrets.get("SMTP_HOST", "smtp.gmail.com")
        port = int(st.secrets.get("SMTP_PORT", 587))
        user = st.secrets.get("SMTP_USER", "")
        password = st.secrets.get("SMTP_PASSWORD", "")
        override = st.secrets.get("ALERT_EMAIL_TO", "")
        to_addrs = [a.strip() for a in override.split(",") if a.strip()] if override else ALERT_EMAILS_TO
        if not user or not password or not to_addrs:
            return
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = ", ".join(to_addrs)
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(user, to_addrs, msg.as_string())
    except Exception:
        pass  # an alert failure should never block a staff submission


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


def card_tickboxes(card_list: list[str], key_prefix: str, preselected: list[str] | None = None) -> list[str]:
    """Renders one checkbox per card name and returns the ticked ones.
    Pass preselected to pre-tick existing choices (used by the Edit Entries
    admin section)."""
    preselected = preselected or []
    picked = []
    cols = st.columns(len(card_list)) if card_list else []
    for col, card in zip(cols, card_list):
        with col:
            if st.checkbox(card, value=(card in preselected), key=f"{key_prefix}_{card}"):
                picked.append(card)
    return picked


def _fetch_bytes(url: str, timeout: int = 15) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read()


# ---- additional funding requests ------------------------------------------
def insert_funding_request(record: dict):
    """Best-effort log for the register — the actual approval happens by
    email, this table just keeps a record of what's been asked for."""
    try:
        get_supabase().table(FUNDING_TABLE).insert(record).execute()
    except Exception:
        pass


def fetch_funding_requests() -> pd.DataFrame:
    try:
        res = get_supabase().table(FUNDING_TABLE).select("*").order("submitted_at", desc=True).execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def update_funding_request(row_id, updates: dict):
    get_supabase().table(FUNDING_TABLE).update(updates).eq("id", row_id).execute()


# ---- additional funding SPEND ledger (actual $ spent, tracked per term) --
def insert_funding_spend(record: dict):
    get_supabase().table(SPEND_TABLE).insert(record).execute()


def fetch_funding_spend(term_label: str | None = None) -> pd.DataFrame:
    q = get_supabase().table(SPEND_TABLE).select("*").order("entered_at", desc=True)
    if term_label:
        q = q.eq("term_label", term_label)
    res = q.execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()


def delete_funding_spend(row_id):
    get_supabase().table(SPEND_TABLE).delete().eq("id", row_id).execute()


def build_funding_request_pdf(data: dict) -> bytes:
    """Builds the Additional Program Funding Request as a proper document —
    header fields in a table, each narrative section as a wrapped paragraph,
    and a Manager sign-off block at the bottom so approval can happen on
    the same page once it's emailed across."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm
    )
    styles = getSampleStyleSheet()
    heading_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading3"], textColor=colors.HexColor("#1A7A7A"),
        spaceBefore=12, spaceAfter=3,
    )
    body_style = ParagraphStyle("Body", parent=styles["Normal"], spaceAfter=4, leading=14)

    story = [
        Paragraph("Cowandilla Learning Centre", styles["Title"]),
        Paragraph("Additional Program Funding Request", styles["Heading2"]),
        Spacer(1, 4),
        Paragraph(
            "Each program is allocated $200 per term. This request draws on the "
            "further $500 per term available for additional program funding.",
            styles["Italic"],
        ),
        Spacer(1, 12),
    ]

    info_table = Table(
        [
            ["Staff Member:", data["staff"], "Program:", data["program"]],
            ["Term:", data["term"], "Requested Amount:", f"${data['amount']:.2f}"],
        ],
        colWidths=[3.1 * cm, 5.4 * cm, 3.3 * cm, 3.6 * cm],
    )
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 10))

    for label, text in [
        ("Purpose", data["purpose"]),
        ("Connection to Curriculum", data["curriculum"]),
        ("Genuine Value", data["value"]),
        ("Continual Learning for Students", data["learning"]),
    ]:
        story.append(Paragraph(label, heading_style))
        story.append(Paragraph((text or "").replace("\n", "<br/>"), body_style))

    story.append(Spacer(1, 16))
    story.append(Paragraph(f"Submitted by: {data['staff']}   —   Date: {data['date']}", body_style))
    story.append(Paragraph(
        "Electronically confirmed as accurate at time of submission (stands in place of signature).",
        styles["Italic"],
    ))

    story.append(Spacer(1, 26))
    story.append(Paragraph("Manager Approval", heading_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Approved &nbsp;&nbsp;☐ &nbsp;&nbsp;&nbsp;&nbsp; Declined &nbsp;&nbsp;☐", body_style))
    story.append(Paragraph("Approved amount (if different): $ _______________", body_style))
    story.append(Spacer(1, 22))
    story.append(Paragraph("Signature: ______________________________ &nbsp;&nbsp;&nbsp; Date: ______________", body_style))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


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

tab_request, tab_return, tab_funding, tab_spend, tab_register, tab_admin = st.tabs(
    ["1️⃣ Request Card", "2️⃣ Return Card", "💰 Additional Funding", "📊 Funding Spent", "📋 Register", "🔒 Admin"]
)

# ------------------------------------------------------------------ STEP 1
with tab_request:
    st.subheader("Request a card (Form 1)")
    st.write("Fill this in before taking a CLC credit card, so admin can approve it up front.")

    with st.form("request_card_form", clear_on_submit=True):
        req_staff = st.selectbox("Staff Member", STAFF_LIST, key="req_staff") if STAFF_LIST else None
        if not STAFF_LIST:
            st.warning("No staff members set up yet — add some in the Admin tab first.")

        req_budget = st.selectbox("Budget", BUDGET_OPTIONS, key="req_budget")

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
        elif not req_budget:
            st.error("Select which budget this comes from.")
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
                    "budget": req_budget,
                    "card_names": req_cards,
                    "approx_cost": req_cost,
                    "explanation": req_reason.strip(),
                    "status": REQ_PENDING,
                    "requested_at": now_iso(),
                }
            )
            send_alert_email(
                "Credit Card Request — awaiting approval",
                f"{req_staff} has requested {', '.join(req_cards)} (budget: {req_budget}) "
                f"— approx ${req_cost:.2f}.\n\nReason given: {req_reason.strip()}\n\n"
                "Open the portal's Credit Card Request & Return tool, Admin tab, "
                "to approve or decline.",
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
            row["id"]: f"{', '.join(row.get('card_names') or [])} — {row.get('budget', '')} — approx "
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
            send_alert_email(
                "Credit Card Return — awaiting approval",
                f"{ret_staff} has submitted a return for {', '.join(linked_request.get('card_names') or [])} "
                f"— ${total_amount:.2f} (receipt dated {format_date(receipt_date.isoformat())}).\n\n"
                "Open the portal's Credit Card Request & Return tool, Admin tab, "
                "to sight the receipt and approve.",
            )
            st.success(f"Return submitted for {ret_staff} — awaiting admin sign-off.")

# -------------------------------------------------------------- FUNDING TAB
with tab_funding:
    st.subheader("Additional Program Funding Request")
    st.write(
        "Each program (JP / PY / SY / NIT / ADMIN) is allocated **$200 per term**. "
        "A further **$500 per term** is available for programs to request additional "
        "funding — in full or in part. This is a genuine application, not a formality, "
        "so take the space to make the case properly. Once you generate the form below, "
        f"download it and email it to your Manager ({MANAGER_EMAIL}) for approval."
    )

    with st.form("funding_request_form", clear_on_submit=True):
        f_staff = st.selectbox("Staff Member", STAFF_LIST, key="fund_staff") if STAFF_LIST else None
        if not STAFF_LIST:
            st.warning("No staff members set up yet — add some in the Admin tab first.")
        f_program = st.selectbox("Program", PROGRAM_OPTIONS, key="fund_program")

        fc1, fc2 = st.columns(2)
        with fc1:
            f_term = st.selectbox("Term", ["Term 1", "Term 2", "Term 3", "Term 4"], key="fund_term")
        with fc2:
            f_year = st.number_input(
                "Year", min_value=2024, max_value=2100, value=date.today().year, step=1, key="fund_year"
            )

        f_amount = st.number_input(
            "Requested amount ($)", min_value=0.0, max_value=500.0, step=1.0, format="%.2f", key="fund_amount"
        )
        f_purpose = st.text_area("Purpose", placeholder="What is the money for?")
        f_curriculum = st.text_area(
            "Connection to curriculum",
            placeholder="How does this connect to the Australian Curriculum / your program's teaching and learning?",
        )
        f_value = st.text_area(
            "Genuine value",
            placeholder="Why is this genuinely worth funding — what's the value beyond \"nice to have\"?",
        )
        f_learning = st.text_area(
            "Continual learning for students",
            placeholder="What ongoing learning or capability will students take from this, beyond the immediate activity?",
        )
        f_confirm = st.checkbox("I confirm this request is accurate and made in good faith.")
        f_submitted = st.form_submit_button("Generate Funding Request Form", type="primary")

    if f_submitted:
        if not f_staff:
            st.error("Select a staff member.")
        elif f_amount <= 0:
            st.error("Enter the requested amount.")
        elif not f_purpose.strip():
            st.error("Describe the purpose.")
        elif not f_curriculum.strip():
            st.error("Describe the connection to curriculum.")
        elif not f_value.strip():
            st.error("Describe the genuine value.")
        elif not f_learning.strip():
            st.error("Describe the continual learning for students.")
        elif not f_confirm:
            st.error("Tick to confirm before generating the form.")
        else:
            term_label = f"{f_term} {int(f_year)}"
            pdf_data = {
                "staff": f_staff,
                "program": f_program,
                "term": term_label,
                "amount": f_amount,
                "purpose": f_purpose.strip(),
                "curriculum": f_curriculum.strip(),
                "value": f_value.strip(),
                "learning": f_learning.strip(),
                "date": format_date(date.today().isoformat()),
            }
            insert_funding_request({
                "staff_member": f_staff,
                "program": f_program,
                "term": term_label,
                "amount": f_amount,
                "purpose": pdf_data["purpose"],
                "curriculum": pdf_data["curriculum"],
                "value_statement": pdf_data["value"],
                "continual_learning": pdf_data["learning"],
                "submitted_at": now_iso(),
            })
            st.session_state["funding_pdf_bytes"] = build_funding_request_pdf(pdf_data)
            st.session_state["funding_pdf_name"] = (
                f"AdditionalFundingRequest_{f_staff.replace(' ', '_')}_{term_label.replace(' ', '_')}.pdf"
            )

    if st.session_state.get("funding_pdf_bytes"):
        st.success("Form ready — download it below, then email it to your Manager for approval.")
        st.download_button(
            "⬇️ Download completed form (PDF)",
            st.session_state["funding_pdf_bytes"],
            file_name=st.session_state.get("funding_pdf_name", "AdditionalFundingRequest.pdf"),
            mime="application/pdf",
        )
        st.info(f"Email the downloaded PDF to your Manager at **{MANAGER_EMAIL}** to have it approved.")

# -------------------------------------------------------------- SPEND TAB
with tab_spend:
    st.subheader("Additional Funding — Spent This Term")
    cur_label, cur_start, cur_end = get_current_term()
    st.caption(f"{cur_label} ({cur_start.strftime('%d/%m/%Y')} – {cur_end.strftime('%d/%m/%Y')})")

    cur_df = fetch_funding_spend(cur_label)
    total_spent = float(cur_df["amount"].sum()) if not cur_df.empty else 0.0
    remaining = TERM_POOL - total_spent

    m1, m2, m3 = st.columns(3)
    m1.metric("Term pool", f"${TERM_POOL:.2f}")
    m2.metric("Spent so far", f"${total_spent:.2f}")
    m3.metric("Remaining", f"${remaining:.2f}")
    st.progress(min(total_spent / TERM_POOL, 1.0) if TERM_POOL else 0)

    if cur_df.empty:
        st.write("Nothing logged against the additional funding pool yet this term.")
    else:
        disp = cur_df[["program", "amount", "purchase", "entered_at"]].copy()
        disp["entered_at"] = disp["entered_at"].apply(format_dt)
        disp = disp.rename(columns={
            "program": "Program", "amount": "Amount", "purchase": "Purchase", "entered_at": "Logged",
        })
        st.dataframe(disp, use_container_width=True, hide_index=True)

    with st.expander("Previous terms (closed off automatically once their dates pass)"):
        all_spend = fetch_funding_spend(None)
        past_labels = (
            [t for t in all_spend["term_label"].unique() if t != cur_label]
            if not all_spend.empty else []
        )
        if not past_labels:
            st.write("No earlier terms logged yet.")
        else:
            for t in past_labels:
                t_df = all_spend[all_spend["term_label"] == t]
                t_total = float(t_df["amount"].sum())
                st.markdown(f"**{t}** — ${t_total:.2f} spent of ${TERM_POOL:.2f} (${TERM_POOL - t_total:.2f} remaining)")
                t_disp = t_df[["program", "amount", "purchase", "entered_at"]].copy()
                t_disp["entered_at"] = t_disp["entered_at"].apply(format_dt)
                st.dataframe(
                    t_disp.rename(columns={
                        "program": "Program", "amount": "Amount", "purchase": "Purchase", "entered_at": "Logged",
                    }),
                    use_container_width=True, hide_index=True,
                )

# ------------------------------------------------------------------ STEP 3
with tab_register:
    st.subheader("Full register")
    reg_view = st.radio("Show", ["Card Requests", "Card Returns", "Additional Funding Requests"], horizontal=True)

    if reg_view == "Card Requests":
        status_filter = st.selectbox("Filter by status", ["All", REQ_PENDING, REQ_APPROVED, REQ_DECLINED, "Completed"])
        df = fetch_requests(None if status_filter == "All" else status_filter)
        cols = ["staff_member", "budget", "card_names", "approx_cost", "explanation", "status",
                "requested_at", "admin_approved_by", "admin_approved_at"]
        dt_cols, date_cols = ["requested_at", "admin_approved_at"], []
    elif reg_view == "Card Returns":
        status_filter = st.selectbox("Filter by status", ["All", RET_PENDING, RET_APPROVED, RET_RETURNED])
        df = fetch_submissions(None if status_filter == "All" else status_filter)
        cols = ["staff_member", "card_names", "receipt_date", "total_amount", "status",
                "submitted_at", "admin_approved_by", "admin_approved_at", "notes"]
        dt_cols, date_cols = ["submitted_at", "admin_approved_at"], ["receipt_date"]
    else:
        st.caption("Approval for these happens by email to the Manager — this is a record of what's been submitted, not a pending-approval queue.")
        df = fetch_funding_requests()
        cols = ["staff_member", "program", "term", "amount", "purpose", "curriculum",
                "value_statement", "continual_learning", "submitted_at"]
        dt_cols, date_cols = ["submitted_at"], []

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
        ["Approve Requests", "Approve Returns", "Edit Entries", "View & Download Forms",
         "Log Funding Spend", "Manage Staff & Cards"],
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
                        st.markdown(f"**{row['staff_member']}** — {cards} — {row.get('budget', '')} — approx ${row['approx_cost']:.2f}")
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

    elif admin_section == "Edit Entries":
        st.write(
            "Fix a staff data-entry mistake here — e.g. the wrong budget/program "
            "ticked, a typo in the amount, or the wrong card selected. This edits "
            "the record directly; it doesn't change approval status."
        )
        edit_type = st.selectbox(
            "What are you fixing?", ["Card Request", "Card Return", "Additional Funding Request"], key="edit_type"
        )

        if edit_type == "Card Request":
            edit_df = fetch_requests(None)
            if edit_df.empty:
                st.write("No requests to edit.")
            else:
                options = {
                    r["id"]: f"#{r['id']} — {r['staff_member']} — {r.get('budget', '')} — "
                    f"${r['approx_cost']:.2f} — {r['status']} — {format_date(r['requested_at'])}"
                    for _, r in edit_df.iterrows()
                }
                pick_id = st.selectbox("Select request", options.keys(), format_func=lambda i: options[i])
                row = edit_df[edit_df["id"] == pick_id].iloc[0]

                with st.form(f"edit_request_form_{pick_id}"):
                    e_staff = st.selectbox(
                        "Staff Member", STAFF_LIST,
                        index=STAFF_LIST.index(row["staff_member"]) if row["staff_member"] in STAFF_LIST else 0,
                    )
                    e_budget = st.selectbox(
                        "Budget", BUDGET_OPTIONS,
                        index=BUDGET_OPTIONS.index(row.get("budget")) if row.get("budget") in BUDGET_OPTIONS else 0,
                    )
                    st.write("Card(s)")
                    e_cards = card_tickboxes(CARD_LIST, f"editreq_{pick_id}", preselected=row.get("card_names") or [])
                    e_cost = st.number_input(
                        "Approximate cost ($)", min_value=0.0, step=0.01, format="%.2f",
                        value=float(row["approx_cost"]),
                    )
                    e_explanation = st.text_area("Explanation", value=row.get("explanation") or "")
                    e_status = st.selectbox(
                        "Status", [REQ_PENDING, REQ_APPROVED, REQ_DECLINED, "Completed"],
                        index=[REQ_PENDING, REQ_APPROVED, REQ_DECLINED, "Completed"].index(row["status"])
                        if row["status"] in [REQ_PENDING, REQ_APPROVED, REQ_DECLINED, "Completed"] else 0,
                    )
                    if st.form_submit_button("Save corrections", type="primary"):
                        update_request(pick_id, {
                            "staff_member": e_staff,
                            "budget": e_budget,
                            "card_names": e_cards,
                            "approx_cost": e_cost,
                            "explanation": e_explanation,
                            "status": e_status,
                        })
                        st.success(f"Request #{pick_id} updated.")
                        st.rerun()

        elif edit_type == "Card Return":
            edit_df = fetch_submissions(None)
            if edit_df.empty:
                st.write("No returns to edit.")
            else:
                options = {
                    r["id"]: f"#{r['id']} — {r['staff_member']} — ${r['total_amount']:.2f} — "
                    f"{r['status']} — {format_date(r.get('receipt_date'))}"
                    for _, r in edit_df.iterrows()
                }
                pick_id = st.selectbox("Select return", options.keys(), format_func=lambda i: options[i])
                row = edit_df[edit_df["id"] == pick_id].iloc[0]

                with st.form(f"edit_return_form_{pick_id}"):
                    e_staff = st.selectbox(
                        "Staff Member", STAFF_LIST,
                        index=STAFF_LIST.index(row["staff_member"]) if row["staff_member"] in STAFF_LIST else 0,
                    )
                    st.write("Card(s)")
                    e_cards = card_tickboxes(CARD_LIST, f"editret_{pick_id}", preselected=row.get("card_names") or [])
                    e_receipt_date = st.date_input(
                        "Date on receipt",
                        value=pd.to_datetime(row["receipt_date"]).date() if row.get("receipt_date") else date.today(),
                    )
                    e_total = st.number_input(
                        "Total on receipt ($)", min_value=0.0, step=0.01, format="%.2f",
                        value=float(row["total_amount"]),
                    )
                    e_notes = st.text_area("Notes", value=row.get("notes") or "")
                    e_status = st.selectbox(
                        "Status", [RET_PENDING, RET_APPROVED, RET_RETURNED],
                        index=[RET_PENDING, RET_APPROVED, RET_RETURNED].index(row["status"])
                        if row["status"] in [RET_PENDING, RET_APPROVED, RET_RETURNED] else 0,
                    )
                    if st.form_submit_button("Save corrections", type="primary"):
                        update_submission(pick_id, {
                            "staff_member": e_staff,
                            "card_names": e_cards,
                            "receipt_date": e_receipt_date.isoformat(),
                            "total_amount": e_total,
                            "notes": e_notes,
                            "status": e_status,
                        })
                        st.success(f"Return #{pick_id} updated.")
                        st.rerun()

        else:  # Additional Funding Request
            edit_df = fetch_funding_requests()
            if edit_df.empty:
                st.write("No funding requests to edit.")
            else:
                options = {
                    r["id"]: f"#{r['id']} — {r['staff_member']} — {r['program']} — "
                    f"{r['term']} — ${r['amount']:.2f}"
                    for _, r in edit_df.iterrows()
                }
                pick_id = st.selectbox("Select funding request", options.keys(), format_func=lambda i: options[i])
                row = edit_df[edit_df["id"] == pick_id].iloc[0]

                with st.form(f"edit_funding_form_{pick_id}"):
                    e_staff = st.selectbox(
                        "Staff Member", STAFF_LIST,
                        index=STAFF_LIST.index(row["staff_member"]) if row["staff_member"] in STAFF_LIST else 0,
                    )
                    e_program = st.selectbox(
                        "Program", PROGRAM_OPTIONS,
                        index=PROGRAM_OPTIONS.index(row["program"]) if row["program"] in PROGRAM_OPTIONS else 0,
                    )
                    e_term = st.text_input("Term", value=row.get("term") or "")
                    e_amount = st.number_input(
                        "Requested amount ($)", min_value=0.0, step=1.0, format="%.2f", value=float(row["amount"]),
                    )
                    e_purpose = st.text_area("Purpose", value=row.get("purpose") or "")
                    e_curriculum = st.text_area("Connection to curriculum", value=row.get("curriculum") or "")
                    e_value = st.text_area("Genuine value", value=row.get("value_statement") or "")
                    e_learning = st.text_area("Continual learning for students", value=row.get("continual_learning") or "")
                    if st.form_submit_button("Save corrections", type="primary"):
                        update_funding_request(pick_id, {
                            "staff_member": e_staff,
                            "program": e_program,
                            "term": e_term,
                            "amount": e_amount,
                            "purpose": e_purpose,
                            "curriculum": e_curriculum,
                            "value_statement": e_value,
                            "continual_learning": e_learning,
                        })
                        st.success(f"Funding request #{pick_id} updated.")
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

    elif admin_section == "Log Funding Spend":
        cur_label, cur_start, cur_end = get_current_term()
        st.write(
            f"Logging against **{cur_label}** ({cur_start.strftime('%d/%m/%Y')} – "
            f"{cur_end.strftime('%d/%m/%Y')}) — worked out automatically from today's date, "
            "so this closes off and rolls to the next term on its own."
        )

        with st.form("log_spend_form", clear_on_submit=True):
            sp_program = st.selectbox("Program", PROGRAM_OPTIONS, key="sp_program")
            sp_amount = st.number_input("Amount spent ($)", min_value=0.0, step=1.0, format="%.2f", key="sp_amount")
            sp_purchase = st.text_area("What was purchased", key="sp_purchase")
            sp_submitted = st.form_submit_button("Add entry", type="primary")

        if sp_submitted:
            if sp_amount <= 0:
                st.error("Enter an amount.")
            elif not sp_purchase.strip():
                st.error("Describe what was purchased.")
            else:
                insert_funding_spend({
                    "term_label": cur_label,
                    "program": sp_program,
                    "amount": sp_amount,
                    "purchase": sp_purchase.strip(),
                    "entered_at": now_iso(),
                })
                st.success("Logged.")
                st.rerun()

        st.markdown(f"**{cur_label} entries so far**")
        term_df = fetch_funding_spend(cur_label)
        if term_df.empty:
            st.write("Nothing logged yet.")
        else:
            term_total = float(term_df["amount"].sum())
            st.caption(f"Total spent: ${term_total:.2f} — ${TERM_POOL - term_total:.2f} remaining of ${TERM_POOL:.2f}.")
            for _, row in term_df.iterrows():
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.write(
                        f"**{row['program']}** — ${row['amount']:.2f} — {row['purchase']} "
                        f"_(logged {format_dt(row['entered_at'])})_"
                    )
                with c2:
                    if st.button("🗑️", key=f"del_spend_{row['id']}"):
                        delete_funding_spend(row["id"])
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
