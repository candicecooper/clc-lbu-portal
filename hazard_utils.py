"""
hazard_utils.py  —  shared helpers for the CLC-LBU Hazard Report tool.

Used by:
  * pages/70_Hazard_Report.py   (the tool itself)
  * the Daily Bulletin page      (render_bulletin_hazards — 2 lines to add)

Put this file at the ROOT of the repo (next to confidential_auth.py).
"""

from __future__ import annotations

import smtplib
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

import streamlit as st

try:
    from zoneinfo import ZoneInfo
    ADL_TZ = ZoneInfo("Australia/Adelaide")
except Exception:  # pragma: no cover
    ADL_TZ = None

# ------------------------------------------------------------------
# Form content (matches the Microsoft Form exactly)
# ------------------------------------------------------------------
LOCATIONS = [
    "Administration", "Meeting Room", "Manager Office", "T.C. Office",
    "Admin Corridor", "Student Kitchen", "Staff Prep Room", "Staff Kitchen",
    "Positive Pathways", "J.P. Room", "Spill Out Room (JP/PY)", "P.Y. Room",
    "S.Y. Room", "Spill Out Room (SY)", "Student Female Toilets",
    "Student Male Toilets", "Staff Female Toilets", "Staff Male Toilets",
    "Playground", "Yard", "Pathway around toilet area",
    "Shed 1 and surrounding", "Shed 2 and pathway", "Carpark",
    "Front Garden and pathway", "Other",
]

# label, short name, emoji, days to respond (0 = same day)
RISK_LEVELS = [
    ("Urgent - immediate response required - Please report this directly to Leadership", "Urgent", "🔴", 0),
    ("Extremely High - response required within the day", "Extremely High", "🔴", 0),
    ("High - response required within 3 days", "High", "🟠", 3),
    ("Medium - response required within 1 week", "Medium", "🟡", 7),
    ("Low - response required within 1 month", "Low", "🟢", 30),
    ("Other", "Other", "⚪", 7),
]
RISK_LABELS = [r[0] for r in RISK_LEVELS]
RISK_SHORT = {r[0]: r[1] for r in RISK_LEVELS}
RISK_EMOJI = {r[1]: r[2] for r in RISK_LEVELS}
RISK_DAYS = {r[1]: r[3] for r in RISK_LEVELS}
RISK_ORDER = {r[1]: i for i, r in enumerate(RISK_LEVELS)}

STATUSES = ["Open", "In progress", "Resolved"]
PHOTO_BUCKET = "hazard-photos"


def today_adl() -> date:
    return datetime.now(ADL_TZ).date() if ADL_TZ else date.today()


def due_date_for(risk_short: str, sighted: date) -> date:
    return sighted + timedelta(days=RISK_DAYS.get(risk_short, 7))


def location_text(row: dict) -> str:
    loc = row.get("location") or ""
    if loc == "Other" and row.get("location_other"):
        return row["location_other"]
    return loc


# ------------------------------------------------------------------
# Secrets — tolerant of the different key names used across the portal
# ------------------------------------------------------------------
def _secret(*paths, default=None):
    """Return the first secret found. Each path is 'KEY' or 'section.key'.
    Checks Streamlit secrets first, then Render environment variables."""
    import os
    for p in paths:
        if "." not in p and os.environ.get(p):
            return os.environ[p]
    for p in paths:
        try:
            node = st.secrets
            for part in p.split("."):
                node = node[part]
            if node:
                return node
        except Exception:
            continue
    return default


# ------------------------------------------------------------------
# Supabase
# ------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_supabase():
    from supabase import create_client

    url = _secret("SUPABASE_URL", "supabase.url", "supabase.SUPABASE_URL", "connections.supabase.url")
    key = _secret("SUPABASE_KEY", "SUPABASE_ANON_KEY", "supabase.key", "supabase.anon_key",
                  "supabase.SUPABASE_KEY", "connections.supabase.key")
    if not url or not key:
        raise RuntimeError("Supabase URL/key not found in Streamlit secrets.")
    return create_client(url, key)


def fetch_hazards(status_filter: list[str] | None = None) -> list[dict]:
    sb = get_supabase()
    q = sb.table("hazard_reports").select("*").order("created_at", desc=True)
    if status_filter:
        q = q.in_("status", status_filter)
    return q.execute().data or []


def fetch_open_hazards() -> list[dict]:
    rows = fetch_hazards(["Open", "In progress"])
    rows.sort(key=lambda r: (RISK_ORDER.get(r.get("risk_level"), 99), r.get("date_sighted") or ""))
    return rows


# ------------------------------------------------------------------
# Email (same Gmail sender account as the Credit Card tool)
# ------------------------------------------------------------------
def _smtp_settings():
    user = _secret("GMAIL_USER", "SMTP_USER", "EMAIL_USER", "EMAIL_SENDER", "gmail.user",
                   "gmail.address", "smtp.user", "smtp.username", "email.user", "email.sender",
                   default="clc.digitalstaffmeeting@gmail.com")
    pw = _secret("GMAIL_APP_PASSWORD", "GMAIL_PASSWORD", "SMTP_PASSWORD", "EMAIL_PASSWORD",
                 "gmail.app_password", "gmail.password", "smtp.password", "email.password")
    host = _secret("SMTP_HOST", "smtp.host", "smtp.server", default="smtp.gmail.com")
    port = int(_secret("SMTP_PORT", "smtp.port", default=587))
    return user, pw, host, port


def _send_via_webhook(url: str, token: str, recipients: list[str], subject: str, html: str) -> tuple[bool, str]:
    """Send through a Google Apps Script web app on the CLC Gmail account (plain HTTPS,
    so it works on Render's free plan, which blocks email ports)."""
    import json
    import urllib.request

    body = json.dumps({"token": token, "to": ",".join(recipients), "subject": subject, "html": html}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        reply = resp.read().decode(errors="ignore").strip()
    if reply.startswith("OK"):
        return True, f"Email sent to {len(recipients)} recipient(s)."
    return False, f"Email failed: Apps Script replied '{reply[:150]}'"


def _send_via_smtp(user, pw, host, port, recipients, msg) -> None:
    """Try the configured port first, then the other Gmail port (587 STARTTLS / 465 SSL)."""
    errors = []
    for p in dict.fromkeys([port, 587, 465]):
        try:
            if p == 465:
                with smtplib.SMTP_SSL(host, 465, timeout=20) as s:
                    s.login(user, pw)
                    s.sendmail(user, recipients, msg.as_string())
            else:
                with smtplib.SMTP(host, p, timeout=20) as s:
                    s.starttls()
                    s.login(user, pw)
                    s.sendmail(user, recipients, msg.as_string())
            return
        except smtplib.SMTPAuthenticationError as e:
            raise RuntimeError(f"Gmail rejected the login ({e.smtp_code}) – check the app password") from e
        except Exception as e:
            errors.append(f"port {p}: {e or type(e).__name__}")
    raise RuntimeError("; ".join(errors) + ". If this keeps happening, your host is blocking email ports – "
                                           "set up EMAIL_WEBHOOK_URL (see setup notes).")


def send_hazard_email(row: dict, recipients: list[str], portal_url: str | None = None) -> tuple[bool, str]:
    if not recipients:
        return False, "No active email recipients are set up (Manage → Settings)."
    user, pw, host, port = _smtp_settings()
    webhook = _secret("EMAIL_WEBHOOK_URL", "email.webhook_url", "gmail.webhook_url")
    webhook_token = _secret("EMAIL_WEBHOOK_TOKEN", "email.webhook_token", "gmail.webhook_token", default="")
    if not pw and not webhook:
        return False, "Email password not found in Streamlit secrets."

    risk = row.get("risk_level", "")
    emoji = RISK_EMOJI.get(risk, "⚠️")
    loc = location_text(row)
    subject = f"{emoji} {risk.upper()} hazard – {loc} – {row.get('hazard', '')[:60]}"

    urgent_banner = ""
    if risk == "Urgent":
        urgent_banner = ("<p style='background:#b91c1c;color:#fff;padding:10px;border-radius:6px'>"
                         "<b>URGENT – immediate response required.</b> The reporter has been told to "
                         "also report this directly to Leadership.</p>")

    def tr(k, v):
        return (f"<tr><td style='padding:6px 10px;color:#555;vertical-align:top'><b>{escape(k)}</b></td>"
                f"<td style='padding:6px 10px'>{escape(str(v or '—'))}</td></tr>")

    risk_disp = risk if risk != "Other" else f"Other – {row.get('risk_other') or ''}"
    html = f"""
    <div style='font-family:Segoe UI,Arial,sans-serif;font-size:14px'>
      <h2 style='margin:0 0 8px'>CLC Potential Hazard Report</h2>
      {urgent_banner}
      <table style='border-collapse:collapse;border:1px solid #ddd'>
        {tr('Risk level', risk_disp)}
        {tr('Respond by', row.get('due_date'))}
        {tr('Location', loc)}
        {tr('Hazard', row.get('hazard'))}
        {tr('Further explanation', row.get('explanation'))}
        {tr('Date sighted', row.get('date_sighted'))}
        {tr('Reported by', row.get('reporter_name'))}
        {tr('Photos attached in tool', len(row.get('photo_paths') or []))}
      </table>
      <p style='margin-top:14px'>Update or resolve this hazard in the portal's <b>Hazard Report</b> tool
      (Manage tab){f": <a href='{portal_url}'>{portal_url}</a>" if portal_url else ""}.
      It will show in the Daily Bulletin until it is marked Resolved.</p>
    </div>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"CLC Portal <{user}>"
    msg["To"] = ", ".join(recipients)
    if risk in ("Urgent", "Extremely High"):
        msg["X-Priority"] = "1"
        msg["Importance"] = "High"
    msg.attach(MIMEText(html, "html"))

    # 1. Web route (works on Render free plan) if it has been set up
    if webhook:
        try:
            return _send_via_webhook(webhook, webhook_token, recipients, subject, html)
        except Exception as e:
            if not pw:
                return False, f"Email failed: {e}"
    # 2. Gmail SMTP (needs a host that allows email ports)
    try:
        _send_via_smtp(user, pw, host, port, recipients, msg)
        return True, f"Email sent to {len(recipients)} recipient(s)."
    except Exception as e:  # keep the report saved even if email fails
        return False, f"Email failed: {e}"


# ------------------------------------------------------------------
# Daily Bulletin snippet
# ------------------------------------------------------------------
def render_bulletin_hazards(heading: str = "⚠️ Current Site Hazards", show_when_empty: bool = False):
    """Call this from the Daily Bulletin page. Shows every hazard that is
    not yet Resolved, as one short line each. Never breaks the bulletin."""
    try:
        rows = fetch_open_hazards()
    except Exception:
        return
    if not rows and not show_when_empty:
        return

    st.markdown(f"#### {heading}")
    if not rows:
        st.caption("No open hazards.")
        return

    lines = []
    for r in rows:
        risk = r.get("risk_level", "")
        em = RISK_EMOJI.get(risk, "⚠️")
        hz = escape((r.get("hazard") or "").strip())
        if len(hz) > 70:
            hz = hz[:67] + "…"
        status = " <i>(being actioned)</i>" if r.get("status") == "In progress" else ""
        lines.append(f"{em} <b>{escape(location_text(r))}</b> – {hz}"
                     f" <span style='color:#888;font-size:0.85em'>[{escape(risk)}]</span>{status}")
    st.markdown(
        "<div style='border-left:4px solid #d97706;background:rgba(217,119,6,0.08);"
        "padding:8px 12px;border-radius:4px;line-height:1.7'>"
        + "<br>".join(lines)
        + "<div style='font-size:0.8em;color:#888;margin-top:4px'>Please take care around these areas. "
          "Report new hazards in the Hazard Report tool.</div></div>",
        unsafe_allow_html=True,
    )
