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
    """Build a friendly news-digest email for a batch of articles with detailed descriptions.

    Returns {"subject": str, "text": str, "html": str}
    """
    heading = f"Your {period_label} News Digest" if period_label else "Your News Digest"
    subject = f"📰 {heading} - CandorNews ({len(articles)} articles)"

    text_lines = [f"Hi {user_name},", "", f"Here are the {len(articles)} top stories from your interests:", "", "=" * 60, ""]
    html_articles = []

    if articles:
        for idx, article in enumerate(articles, 1):
            title = article.get("title", "Untitled")
            source = article.get("source", "")
            trust_score = article.get("trustScore")
            url = article.get("url", "")
            description = article.get("description", "")
            date = article.get("date", "")

            # Build text version with detailed description
            text_line = f"{idx}. {title}"
            text_lines.append(text_line)
            text_lines.append(f"   Source: {source}")
            if trust_score is not None:
                text_lines.append(f"   Trust Score: {trust_score}%")
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
                text_lines.append(f"   Read more: {url}")
            
            text_lines.append("")  # blank line between articles
            text_lines.append("-" * 60)
            text_lines.append("")

            # Build HTML version with rich formatting
            html_articles.append(
                f"""
                <div style="margin-bottom: 24px; padding: 16px; background: #f9f9f9; border-left: 4px solid #667eea; border-radius: 4px;">
                  <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
                    <span style="font-size: 18px; font-weight: 600; color: #333;">{idx}.</span>
                    <span style="background: #667eea; color: white; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: 600;">{trust_score}% Trust</span>
                  </div>
                  <h3 style="margin: 0 0 10px 0; font-size: 16px; line-height: 1.4; color: #0f172a;">{title}</h3>
                  <div style="color: #666; font-size: 12px; margin-bottom: 12px;">
                    <span>{source}</span>
                    {f' • <span>{date}</span>' if date else ''}
                  </div>
                  {f'<p style="color: #555; font-size: 14px; line-height: 1.6; margin: 12px 0; color: #444;">{description}</p>' if description else ''}
                  {f'<a href="{url}" style="display: inline-block; background: #667eea; color: white; text-decoration: none; padding: 8px 16px; border-radius: 4px; font-size: 13px; font-weight: 600;">Read Full Article →</a>' if url else ''}
                </div>
                """
            )
    else:
        text_lines.append("No new articles right now - check the app for the latest news!")
        html_articles.append('<div style="text-align: center; padding: 20px; color: #999;">No new articles right now - check the app for the latest news!</div>')

    text_lines.append("")
    text_lines.append("")
    text_lines.append("Best regards,")
    text_lines.append("CandorNews Team")
    text_body = "\n".join(text_lines)

    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; background: #fff;">
      <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
        <h1 style="color: white; margin: 0 0 10px 0; font-size: 28px;">📰 {heading}</h1>
        <p style="color: rgba(255,255,255,0.9); margin: 0; font-size: 14px;">Top {len(articles)} stories from your interests</p>
      </div>
      <div style="padding: 30px;">
        <p style="color: #333; font-size: 16px; margin-bottom: 20px;">Hi {user_name},</p>
        <p style="color: #666; font-size: 14px; margin-bottom: 24px;">Here are the {len(articles)} latest news articles selected based on your interests. Each includes a brief summary for quick reading.</p>
        <div style="border-top: 2px solid #eee; padding-top: 20px;">
          {''.join(html_articles)}
        </div>
      </div>
      <div style="background: #f5f5f5; padding: 20px; text-align: center; border-top: 1px solid #ddd;">
        <p style="color: #999; font-size: 12px; margin: 0 0 10px 0;">
          You're receiving this because you enabled email notifications in CandorNews.
        </p>
        <p style="color: #999; font-size: 12px; margin: 0;">
          Manage your preferences anytime in your Profile settings.
        </p>
      </div>
    </div>
    """

    return {"subject": subject, "text": text_body, "html": html_body}
