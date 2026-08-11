"""
Email notification service using SMTP (works with Gmail, Outlook, or any
SMTP provider).

Setup:
1. Choose an SMTP provider. For Gmail, create an "App Password" at
   https://myaccount.google.com/apppasswords (regular password won't work
   if 2FA is enabled).
2. Set the following environment variables (see backend/.env.example):
     SMTP_HOST=smtp.gmail.com
     SMTP_PORT=587
     SMTP_USERNAME=your_email@gmail.com
     SMTP_PASSWORD=your_app_password
     SMTP_FROM_EMAIL=your_email@gmail.com
     SMTP_FROM_NAME=CandorNews

If credentials are not configured, all functions no-op and return a clear
error so the rest of the app keeps working in demo mode.
"""
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587") or "587")
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "") or SMTP_USERNAME
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "CandorNews")


def is_configured() -> bool:
    """Return True if SMTP credentials are set to real values."""
    placeholder_markers = ("your_", "changeme", "xxxx")

    def _looks_real(value: str) -> bool:
        if not value:
            return False
        lowered = value.lower()
        return not any(marker in lowered for marker in placeholder_markers)

    return (
        _looks_real(SMTP_HOST)
        and _looks_real(SMTP_USERNAME)
        and _looks_real(SMTP_PASSWORD)
        and _looks_real(SMTP_FROM_EMAIL)
    )


def send_email(to_email: str, subject: str, body_text: str, body_html: str = None) -> dict:
    """
    Send an email via SMTP.

    Returns a dict: {"success": bool, "message": str}
    """
    if not to_email:
        return {"success": False, "message": "No email address provided."}

    if not is_configured():
        logger.warning(
            "Email notification skipped (SMTP not configured): %s", subject
        )
        return {
            "success": False,
            "message": (
                "Email notifications are not configured on the server. "
                "Set SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD and SMTP_FROM_EMAIL."
            ),
        }

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg["To"] = to_email

        msg.attach(MIMEText(body_text, "plain"))
        if body_html:
            msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM_EMAIL, [to_email], msg.as_string())

        return {"success": True, "message": "Email sent successfully."}

    except smtplib.SMTPAuthenticationError:
        logger.exception("SMTP authentication failed")
        return {"success": False, "message": "SMTP authentication failed. Check SMTP_USERNAME/SMTP_PASSWORD."}
    except Exception as exc:
        logger.exception("Error sending email via SMTP")
        return {"success": False, "message": f"Failed to send email: {exc}"}


def build_news_digest_email(user_name: str, articles: list, period_label: str = "") -> dict:
    """Build a friendly news-digest email for a batch of articles.

    Returns {"subject": str, "text": str, "html": str}
    """
    heading = f"Your {period_label} News Digest" if period_label else "Your News Digest"
    subject = f"📰 {heading} - CandorNews"

    text_lines = [f"Hi {user_name},", "", f"Here's {heading.lower()} from CandorNews:", ""]
    html_articles = []

    if articles:
        for article in articles:
            title = article.get("title", "Untitled")
            source = article.get("source", "")
            trust_score = article.get("trustScore")
            url = article.get("url", "")

            text_line = f"- {title}"
            if source:
                text_line += f" ({source})"
            if trust_score is not None:
                text_line += f" - {trust_score}% Trust"
            text_lines.append(text_line)

            html_articles.append(
                f"""
                <li style="margin-bottom: 14px;">
                  <strong>{title}</strong><br/>
                  <span style="color:#666;font-size:13px;">{source}
                  {f' &middot; {trust_score}% Trust' if trust_score is not None else ''}</span>
                  {f'<br/><a href="{url}" style="color:#667eea;">Read more</a>' if url else ''}
                </li>
                """
            )
    else:
        text_lines.append("No new articles right now - check the app for the latest news!")
        html_articles.append("<li>No new articles right now - check the app for the latest news!</li>")

    text_lines.append("")
    text_lines.append("- CandorNews")
    text_body = "\n".join(text_lines)

    html_body = f"""
    <div style="font-family: -apple-system, Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <h2 style="color:#667eea;">📰 {heading}</h2>
      <p>Hi {user_name},</p>
      <p>Here are the latest headlines from CandorNews:</p>
      <ul style="padding-left: 18px;">
        {''.join(html_articles)}
      </ul>
      <p style="color:#999;font-size:12px;margin-top:30px;">
        You're receiving this because you enabled email notifications in CandorNews.
        You can change your preferences anytime in your Profile.
      </p>
    </div>
    """

    return {"subject": subject, "text": text_body, "html": html_body}
