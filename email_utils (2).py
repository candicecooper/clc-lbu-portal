"""
email_utils.py — CLC Staff Portal email notifications
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st


def _get_smtp_config():
    try:
        smtp = st.secrets.get("smtp", {})
        return {
            "host":     smtp.get("host", "smtp.gmail.com"),
            "port":     int(smtp.get("port", 587)),
            "user":     smtp.get("user", ""),
            "password": smtp.get("password", ""),
            "from_name": smtp.get("from_name", "CLC Staff Portal"),
        }
    except Exception:
        return {"host": "smtp.gmail.com", "port": 587, "user": "", "password": "", "from_name": "CLC Staff Portal"}


def send_edition_notification(recipient_emails: list, edition_title: str, edition_id: str, app_url: str = "") -> bool:
    """Send email notification when a new edition is published."""
    cfg = _get_smtp_config()
    if not cfg["user"] or not cfg["password"]:
        return False
    if not recipient_emails:
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"📋 New Staff Meeting Edition: {edition_title}"
        msg["From"]    = f"{cfg['from_name']} <{cfg['user']}>"
        msg["To"]      = ", ".join(recipient_emails)
        body = f"""
        <html><body style="font-family:sans-serif;color:#1a2e44;">
        <div style="max-width:600px;margin:0 auto;padding:20px;">
          <h2 style="color:#1A7A7A;">📋 New Staff Meeting Edition</h2>
          <p>A new edition has been published: <strong>{edition_title}</strong></p>
          {f'<p><a href="{app_url}" style="background:#1A7A7A;color:white;padding:8px 16px;border-radius:6px;text-decoration:none;">View Edition</a></p>' if app_url else ""}
          <hr style="border:1px solid #e0e8dc;margin:20px 0;">
          <p style="font-size:0.8rem;color:#888;">Cowandilla Learning Centre — LBU Staff Portal</p>
        </div>
        </body></html>
        """
        msg.attach(MIMEText(body, "html"))
        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["user"], recipient_emails, msg.as_string())
        return True
    except Exception as e:
        st.warning(f"Email notification failed: {e}")
        return False
