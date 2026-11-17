"""Proof that a user owns their email address before any digest is sent.

A 6-digit code is emailed to the account address. Only a keyed hash of the
code is stored. Limits stop the feature being used to flood someone else's
inbox: one code per minute, five codes per day, five attempts per code, and
codes expire after 15 minutes.
"""
from datetime import datetime, timedelta
import hashlib
import hmac
import html
import secrets

from app.core.config import settings

CODE_TTL = timedelta(minutes=15)
RESEND_COOLDOWN = timedelta(seconds=60)
MAX_CODES_PER_DAY = 5
MAX_ATTEMPTS = 5
SEND_NOW_COOLDOWN = timedelta(seconds=60)


def new_code() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def hash_code(email: str, code: str) -> str:
    message = f"{email.lower()}:{code.strip()}".encode("utf-8")
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), message, hashlib.sha256).hexdigest()


def wait_seconds(last: datetime | None, cooldown: timedelta, now: datetime) -> int:
    """Seconds left before an action is allowed again (0 when allowed)."""
    if not last:
        return 0
    remaining = (last + cooldown - now).total_seconds()
    return max(0, int(remaining + 0.999))


def can_send_code(state: dict, now: datetime) -> tuple[bool, str]:
    """Check the resend cooldown and daily limit for verification codes."""
    sent_at = state.get("sent_at")
    wait = wait_seconds(sent_at, RESEND_COOLDOWN, now)
    if wait:
        return False, f"Please wait {wait} seconds before requesting another code."
    if state.get("day") == now.date().isoformat() and state.get("day_count", 0) >= MAX_CODES_PER_DAY:
        return False, "Too many codes requested today. Please try again tomorrow."
    return True, ""


def record_code(state: dict, email: str, code: str, now: datetime) -> dict:
    today = now.date().isoformat()
    return {
        "code_hash": hash_code(email, code),
        "expires_at": now + CODE_TTL,
        "attempts": 0,
        "sent_at": now,
        "day": today,
        "day_count": (state.get("day_count", 0) if state.get("day") == today else 0) + 1,
    }


def check_code(state: dict, email: str, code: str, now: datetime) -> tuple[str, dict]:
    """Returns (result, new_state); result is one of
    "ok", "missing", "expired", "locked", "wrong"."""
    if not state.get("code_hash"):
        return "missing", state
    if now >= state["expires_at"]:
        return "expired", state
    if state.get("attempts", 0) >= MAX_ATTEMPTS:
        return "locked", state
    if hmac.compare_digest(state["code_hash"], hash_code(email, code or "")):
        return "ok", {k: v for k, v in state.items() if k in ("sent_at", "day", "day_count")}
    return "wrong", {**state, "attempts": state.get("attempts", 0) + 1}


def build_code_email(name: str, code: str) -> dict:
    minutes = int(CODE_TTL.total_seconds() // 60)
    text = (f"Hi {name},\n\nYour CandorNews verification code is: {code}\n\n"
            f"Enter it on your Profile page within {minutes} minutes to start receiving news digests.\n"
            "If you did not request this, you can ignore this email.")
    safe_name = html.escape(name or "")
    body = (f"<p>Hi {safe_name},</p><p>Your CandorNews verification code is:</p>"
            f"<p style=\"font-size:28px;font-weight:700;letter-spacing:6px\">{code}</p>"
            f"<p>Enter it on your Profile page within {minutes} minutes to start receiving news digests.</p>"
            "<p style=\"color:#666\">If you did not request this, you can ignore this email.</p>")
    return {"subject": "Your CandorNews verification code", "text": text, "html": body}
