"""Shared look for CandorNews emails, matching the website design:
blue accent (#2563EB / #1D4ED8), slate text, light slate background, the
CandorNews logo, and no emoji. Table layout with inline styles so it renders
the same in Gmail, Outlook and phone mail apps."""
from html import escape

ACCENT = "#2563EB"
ACCENT_DARK = "#1D4ED8"
TEXT = "#0F172A"
TEXT_SECONDARY = "#64748B"
BORDER = "#E2E8F0"
BG = "#F8FAFC"
WHITE = "#FFFFFF"
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
LOGO_PATH = "/CandorNews-removebg-preview.png"


def logo_url(site_url: str) -> str:
    return f"{site_url.rstrip('/')}{LOGO_PATH}" if site_url else ""


def button(href: str, label: str) -> str:
    return (f'<a href="{href}" style="display:inline-block;background-color:{ACCENT};color:{WHITE};'
            f'text-decoration:none;padding:10px 18px;border-radius:8px;font-size:14px;font-weight:600;'
            f'font-family:{FONT};">{escape(label)}</a>')


def badge(label: str) -> str:
    return (f'<span style="display:inline-block;background-color:{ACCENT};'
            f'background-image:linear-gradient(135deg,{ACCENT} 0%,{ACCENT_DARK} 100%);color:{WHITE};'
            f'padding:4px 10px;border-radius:6px;font-size:12px;font-weight:700;">{escape(label)}</span>')


def page(title: str, subtitle: str, content: str, footer: str, site_url: str = "", preheader: str = "") -> str:
    """Wrap email content in the CandorNews frame (header, white card, footer)."""
    logo = logo_url(site_url)
    brand = (f'<img src="{escape(logo, quote=True)}" width="36" height="36" alt="" '
             f'style="display:inline-block;vertical-align:middle;border:0;margin-right:10px;">' if logo else "")
    hidden = (f'<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:{BG};">{escape(preheader)}</div>'
              if preheader else "")
    sub = (f'<p style="margin:6px 0 0 0;color:{TEXT_SECONDARY};font-size:14px;">{escape(subtitle)}</p>'
           if subtitle else "")
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><meta name="supported-color-schemes" content="light"></head>
<body style="margin:0;padding:0;background-color:{BG};">
{hidden}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{BG};">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;font-family:{FONT};">
  <tr><td style="padding:0 4px 16px 4px;">
    {brand}<span style="vertical-align:middle;color:{TEXT};font-size:20px;font-weight:600;">CandorNews</span>
  </td></tr>
  <tr><td style="background-color:{WHITE};border:1px solid {BORDER};border-radius:12px;overflow:hidden;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr><td style="height:4px;line-height:4px;font-size:0;background-color:{ACCENT};
        background-image:linear-gradient(135deg,{ACCENT} 0%,{ACCENT_DARK} 100%);">&nbsp;</td></tr>
      <tr><td style="padding:24px 24px 8px 24px;">
        <h1 style="margin:0;color:{TEXT};font-size:22px;line-height:1.3;font-weight:700;">{escape(title)}</h1>
        {sub}
      </td></tr>
      <tr><td style="padding:16px 24px 24px 24px;color:{TEXT};font-size:15px;line-height:1.6;">
        {content}
      </td></tr>
    </table>
  </td></tr>
  <tr><td style="padding:16px 8px;text-align:center;color:{TEXT_SECONDARY};font-size:12px;line-height:1.6;">
    {footer}
  </td></tr>
</table>
</td></tr>
</table>
</body></html>"""
