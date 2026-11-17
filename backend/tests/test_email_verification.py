"""Email ownership verification before any digest is sent (SEC-03)."""
from datetime import timedelta
from unittest.mock import Mock

import pytest
from httpx import ASGITransport, AsyncClient

from app import main
from app.core.security import create_access_token
from app.models.user import UserCreate
from app.services import email_verification as ev
from app.services.storage import storage_service

EMAIL = "verify@example.com"


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def auth():
    await storage_service.create_user(UserCreate(name="Verify <b>Me</b>", email=EMAIL, password="Test-password-123"))
    return {"Authorization": f"Bearer {create_access_token({'sub': EMAIL})}"}


@pytest.fixture
def outbox(monkeypatch):
    sent = []

    def send(to_email, subject, body_text, body_html=None):
        sent.append({"to": to_email, "subject": subject, "text": body_text, "html": body_html})
        return {"success": True, "message": "ok"}
    monkeypatch.setattr(main.email_service, "send_email", send)
    return sent


def code_from(mail):
    return next(word for word in mail["text"].split() if word.isdigit() and len(word) == 6)


async def _rewind_code_time(seconds):
    user = await storage_service.get_user_by_email(EMAIL)
    state = dict(user.email_verification)
    state["sent_at"] -= timedelta(seconds=seconds)
    state["expires_at"] -= timedelta(seconds=seconds)
    await storage_service.users.update_one({"email": EMAIL}, {"$set": {"email_verification": state}})


async def test_new_accounts_start_unverified(client, auth):
    status = (await client.get("/api/notifications/email/status", headers=auth)).json()
    assert status["email_verified"] is False


async def test_code_verifies_address_and_unlocks_send_now(client, auth, outbox):
    assert (await client.post("/api/notifications/email/test", headers=auth, json={})).status_code == 403
    assert (await client.post("/api/notifications/email/verification", headers=auth)).status_code == 200
    assert len(outbox) == 1 and outbox[0]["to"] == EMAIL and "verification code" in outbox[0]["subject"]
    assert "<b>Me</b>" not in outbox[0]["html"]          # name is escaped
    stored = (await storage_service.get_user_by_email(EMAIL)).email_verification
    assert code_from(outbox[0]) not in str(stored)        # only a hash is stored
    confirmed = await client.post("/api/notifications/email/verification/confirm", headers=auth,
                                  json={"code": code_from(outbox[0])})
    assert confirmed.status_code == 200 and confirmed.json()["email_verified"] is True
    assert (await client.post("/api/notifications/email/test", headers=auth, json={})).status_code == 200
    again = await client.post("/api/notifications/email/test", headers=auth, json={})
    assert again.status_code == 429 and "seconds" in again.json()["detail"]
    assert (await client.post("/api/notifications/email/verification", headers=auth)).status_code == 400


async def test_wrong_codes_are_limited(client, auth, outbox):
    await client.post("/api/notifications/email/verification", headers=auth)
    real = code_from(outbox[0])
    wrong = "000000" if real != "000000" else "111111"
    for _ in range(ev.MAX_ATTEMPTS):
        r = await client.post("/api/notifications/email/verification/confirm", headers=auth, json={"code": wrong})
        assert r.status_code == 400 and "Incorrect" in r.json()["detail"]
    locked = await client.post("/api/notifications/email/verification/confirm", headers=auth, json={"code": real})
    assert locked.status_code == 429
    assert (await storage_service.get_user_by_email(EMAIL)).email_verified is False


async def test_expired_code_is_rejected(client, auth, outbox):
    await client.post("/api/notifications/email/verification", headers=auth)
    await _rewind_code_time(ev.CODE_TTL.total_seconds() + 1)
    r = await client.post("/api/notifications/email/verification/confirm", headers=auth,
                          json={"code": code_from(outbox[0])})
    assert r.status_code == 400 and "expired" in r.json()["detail"]


async def test_confirm_without_code_requested(client, auth):
    r = await client.post("/api/notifications/email/verification/confirm", headers=auth, json={"code": "123456"})
    assert r.status_code == 400 and "Request" in r.json()["detail"]


async def test_resend_cooldown_and_daily_limit(client, auth, outbox):
    assert (await client.post("/api/notifications/email/verification", headers=auth)).status_code == 200
    soon = await client.post("/api/notifications/email/verification", headers=auth)
    assert soon.status_code == 429 and "wait" in soon.json()["detail"]
    for _ in range(ev.MAX_CODES_PER_DAY - 1):
        await _rewind_code_time(61)
        assert (await client.post("/api/notifications/email/verification", headers=auth)).status_code == 200
    await _rewind_code_time(61)
    capped = await client.post("/api/notifications/email/verification", headers=auth)
    assert capped.status_code == 429 and "today" in capped.json()["detail"]
    assert len(outbox) == ev.MAX_CODES_PER_DAY


async def test_failed_delivery_does_not_use_up_the_limit(client, auth, monkeypatch):
    monkeypatch.setattr(main.email_service, "send_email", Mock(return_value={"success": False, "message": "SMTP down"}))
    assert (await client.post("/api/notifications/email/verification", headers=auth)).status_code == 502
    assert (await storage_service.get_user_by_email(EMAIL)).email_verification == {}


def test_long_custom_message_rejected():
    with pytest.raises(Exception):
        main.EmailTestMessage(message="x" * 301)
