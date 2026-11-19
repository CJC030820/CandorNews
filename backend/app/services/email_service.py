from html import escape

from app.services import email_layout as layout
from urllib.parse import quote, urlparse
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


def article_page_url(site_url: str, article_id) -> str:
    """Link to the article's page on the CandorNews website."""
    if not site_url or article_id in (None, ""):
        return ""
    return f"{site_url.rstrip('/')}/article/{quote(str(article_id), safe='')}"


def build_news_digest_email(user_name: str, articles: list, period_label: str = "", site_url: str = "") -> dict:
    """Build a friendly news-digest email for a batch of articles with detailed descriptions.
    Each article links to its page on the CandorNews website (site_url), not
    to the original publisher.

    Returns {"subject": str, "text": str, "html": str}
    """
    heading = f"Your {period_label} News Digest" if period_label else "Your News Digest"
    subject = f"{heading} - CandorNews ({len(articles)} articles)"

    text_lines = [f"Hi {user_name},", "", f"Here are the {len(articles)} recent stories, prioritizing your interests:", "", "=" * 60, ""]
    html_articles = []

    if articles:
        for idx, article in enumerate(articles, 1):
            title = article.get("title", "Untitled")
            source = article.get("source", "")
            trust_score = article.get("trustScore")
            url = article_page_url(site_url, article.get("id"))
            description = article.get("description", "")
            date = article.get("date", "")

            # Build text version with detailed description
            text_line = f"{idx}. {title}"
            text_lines.append(text_line)
            text_lines.append(f"   Source: {source}")
            if trust_score is not None:
                text_lines.append(f"   Trust: {trust_score}/100 (not a truth probability)")
            if date:
                text_lines.append(f"   Published: {date}")
            
            # Add longer description for better preview
            if description:
                # Provide full description or up to 250 chars
                preview = description[:250]
                if len(description) > 250:
                    preview += "..."
                text_lines.append(f"")
                text_lines.append(f"   {preview}")
            
            if url:
                text_lines.append(f"   Read on CandorNews: {url}")
            
            text_lines.append("")  # blank line between articles
            text_lines.append("-" * 60)
            text_lines.append("")

            score_label = f'{trust_score}/100 trust' if trust_score is not None else 'Analysis pending'
            title, source, description, date = [escape(str(value)) for value in (title, source, description, date)]
            url = escape(url, quote=True) if urlparse(url).scheme in {'http', 'https'} else ''
            divider = f"border-top:1px solid {layout.BORDER};" if idx > 1 else ""
            meta = source + (f" &middot; {date}" if date else "")
            html_articles.append(f"""
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
              <td style="padding:18px 0;{divider}">
                {layout.badge(score_label)}
                <h3 style="margin:10px 0 6px 0;font-size:17px;line-height:1.4;color:{layout.TEXT};font-weight:700;">{title}</h3>
                <p style="margin:0 0 10px 0;color:{layout.TEXT_SECONDARY};font-size:13px;">{meta}</p>
                {f'<p style="margin:0 0 14px 0;color:{layout.TEXT};font-size:14px;line-height:1.6;">{description}</p>' if description else ''}
                {layout.button(url, "Read on CandorNews") if url else ''}
              </td>
            </tr></table>"""
            )
    else:
        text_lines.append("No new articles right now - check the app for the latest news!")
        html_articles.append(f'<p style="text-align:center;padding:20px 0;color:{layout.TEXT_SECONDARY};">No new articles right now - check the app for the latest news!</p>')

    text_lines.append("")
    text_lines.append("")
    text_lines.append("Best regards,")
    text_lines.append("CandorNews Team")
    text_body = "\n".join(text_lines)

    user_name = escape(user_name)
    count = len(articles)
    content = (
        f'<p style="margin:0 0 8px 0;">Hi {user_name},</p>'
        f'<p style="margin:0 0 8px 0;color:{layout.TEXT_SECONDARY};font-size:14px;">'
        f'Here are {count} recent news articles, with your interests first. Each has a short summary for quick reading.</p>'
        + "".join(html_articles))
    profile = f"{site_url.rstrip('/')}/profile" if site_url else ""
    manage = (f'<a href="{escape(profile, quote=True)}" style="color:{layout.ACCENT};text-decoration:none;">Profile settings</a>'
              if profile else "Profile settings")
    footer = ("You're receiving this because you turned on email notifications in CandorNews.<br>"
              f"Change delivery times or turn them off anytime in your {manage}.")
    html_body = layout.page(heading, f"Top {count} recent stories", content, footer, site_url,
                            preheader=f"{count} recent stories picked for you")

    return {"subject": subject, "text": text_body, "html": html_body}
