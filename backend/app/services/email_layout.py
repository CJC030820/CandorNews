"""Shared look for CandorNews emails, using the website's colour system:
the same light colours, and the website's dark-mode colours when the reader's
device is in dark mode (Apple Mail, iOS Mail, Outlook and others that support
it). Table layout with inline styles so it renders the same in Gmail, Outlook
and phone mail apps; no emoji.

Light (website :root)              Dark (website [data-theme="dark"])
  page      #FFFFFF  (bg-primary)    #0F172A
  card      #F8FAFC  (bg-secondary)  #1E293B
  text      #0F172A                  #F8FAFC
  secondary #64748B                  #94A3B8
  border    #E2E8F0                  #334155
  accent    #2563EB -> #1D4ED8       #60A5FA -> #3B82F6
"""
from html import escape

# Light mode (inline styles; what every mail app shows by default)
ACCENT = "#2563EB"
ACCENT_DARK = "#1D4ED8"
TEXT = "#0F172A"
TEXT_SECONDARY = "#64748B"
BORDER = "#E2E8F0"
PAGE = "#FFFFFF"
CARD = "#F8FAFC"
BG = PAGE  # small boxes inside the card, such as the verification code
WHITE = "#FFFFFF"

# Dark mode (applied by the <style> block below where the mail app supports it)
DARK_PAGE = "#0F172A"
DARK_CARD = "#1E293B"
DARK_TEXT = "#F8FAFC"
DARK_TEXT_SECONDARY = "#94A3B8"
DARK_BORDER = "#334155"
DARK_ACCENT = "#60A5FA"
DARK_ACCENT_DARK = "#3B82F6"

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
LOGO_PATH = "/CandorNews-removebg-preview.png"

# Class names the dark-mode styles hook onto (inline styles stay the light look).
PAGE_CLASS = "cn-page"
CARD_CLASS = "cn-card"
TEXT_CLASS = "cn-text"
MUTED_CLASS = "cn-muted"
BORDER_CLASS = "cn-border"
LINK_CLASS = "cn-link"
ACCENT_CLASS = "cn-accent"
BOX_CLASS = "cn-box"

_DARK_RULES = f"""
.{PAGE_CLASS} {{ background-color:{DARK_PAGE} !important; }}
.{CARD_CLASS} {{ background-color:{DARK_CARD} !important; border-color:{DARK_BORDER} !important; }}
.{TEXT_CLASS} {{ color:{DARK_TEXT} !important; }}
.{MUTED_CLASS} {{ color:{DARK_TEXT_SECONDARY} !important; }}
.{BORDER_CLASS} {{ border-color:{DARK_BORDER} !important; }}
.{LINK_CLASS} {{ color:{DARK_ACCENT} !important; }}
.{ACCENT_CLASS} {{ background-color:{DARK_ACCENT} !important;
  background-image:linear-gradient(135deg,{DARK_ACCENT} 0%,{DARK_ACCENT_DARK} 100%) !important; color:{WHITE} !important; }}
.{BOX_CLASS} {{ background-color:{DARK_PAGE} !important; border-color:{DARK_BORDER} !important; color:{DARK_ACCENT} !important; }}
"""


def _scoped(rules: str, prefix: str) -> str:
    """The same rules under a selector prefix (Outlook.com marks dark mode with [data-ogsc])."""
    return "\n".join(f"{prefix} {line}" if line.startswith(".") else line for line in rules.strip().splitlines())


STYLE = f"""<style>
:root {{ color-scheme: light dark; supported-color-schemes: light dark; }}
@media (prefers-color-scheme: dark) {{
{_DARK_RULES}
}}
{_scoped(_DARK_RULES, "[data-ogsc]")}
</style>"""


def logo_url(site_url: str) -> str:
    return f"{site_url.rstrip('/')}{LOGO_PATH}" if site_url else ""


def _gradient() -> str:
    return f"background-color:{ACCENT};background-image:linear-gradient(135deg,{ACCENT} 0%,{ACCENT_DARK} 100%);"


def button(href: str, label: str) -> str:
    """Same as the website's "Read More" button: blue gradient, white text, 6px corners."""
    return (f'<a href="{href}" class="{ACCENT_CLASS}" style="display:inline-block;{_gradient()}color:{WHITE};'
            f'text-decoration:none;padding:10px 16px;border-radius:6px;font-size:14px;font-weight:600;'
            f'font-family:{FONT};">{escape(label)}</a>')


def badge(label: str) -> str:
    """Same as the website's trust-score badge."""
    return (f'<span class="{ACCENT_CLASS}" style="display:inline-block;{_gradient()}color:{WHITE};'
            f'padding:4px 10px;border-radius:6px;font-size:12px;font-weight:700;">{escape(label)}</span>')


def page(title: str, subtitle: str, content: str, footer: str, site_url: str = "", preheader: str = "") -> str:
    """Wrap email content in the CandorNews frame (header, card, footer)."""
    logo = logo_url(site_url)
    brand = (f'<img src="{escape(logo, quote=True)}" width="36" height="36" alt="" '
             f'style="display:inline-block;vertical-align:middle;border:0;margin-right:10px;">' if logo else "")
    hidden = (f'<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{escape(preheader)}</div>'
              if preheader else "")
    sub = (f'<p class="{MUTED_CLASS}" style="margin:6px 0 0 0;color:{TEXT_SECONDARY};font-size:14px;">{escape(subtitle)}</p>'
           if subtitle else "")
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark"><meta name="supported-color-schemes" content="light dark">
{STYLE}</head>
<body class="{PAGE_CLASS}" style="margin:0;padding:0;background-color:{PAGE};">
{hidden}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="{PAGE_CLASS}" style="background-color:{PAGE};">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;font-family:{FONT};">
  <tr><td style="padding:0 4px 16px 4px;">
    {brand}<span class="{TEXT_CLASS}" style="vertical-align:middle;color:{TEXT};font-size:20px;font-weight:600;">CandorNews</span>
  </td></tr>
  <tr><td class="{CARD_CLASS}" style="background-color:{CARD};border:1px solid {BORDER};border-radius:12px;overflow:hidden;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr><td class="{ACCENT_CLASS}" style="height:4px;line-height:4px;font-size:0;{_gradient()}">&nbsp;</td></tr>
      <tr><td style="padding:24px 24px 8px 24px;">
        <h1 class="{TEXT_CLASS}" style="margin:0;color:{TEXT};font-size:22px;line-height:1.3;font-weight:700;">{escape(title)}</h1>
        {sub}
      </td></tr>
      <tr><td class="{TEXT_CLASS}" style="padding:16px 24px 24px 24px;color:{TEXT};font-size:15px;line-height:1.6;">
        {content}
      </td></tr>
    </table>
  </td></tr>
  <tr><td class="{MUTED_CLASS}" style="padding:16px 8px;text-align:center;color:{TEXT_SECONDARY};font-size:12px;line-height:1.6;">
    {footer}
  </td></tr>
</table>
</td></tr>
</table>
</body></html>"""
