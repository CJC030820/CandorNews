"""Forgot password: reset with a code emailed to the account address."""
import time
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app import main
from app.core.security import create_access_token
from app.models.user import UserCreate
from app.services import email_verification as ev
from app.services.storage import storage_service

EMAIL = "forgot@example.com"
OLD, NEW = "Old-password-123", "New-password-456"


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def account():
    await storage_service.create_user(UserCreate(name="Forgetful", email=EMAIL, password=OLD))


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


async def login(client, password):
    return await client.post("/api/auth/login", json={"email": EMAIL, "password": password})


async def test_reset_with_emailed_code_changes_the_password(client, account, outbox):
    r = await client.post("/api/auth/password-reset/request", json={"email": EMAIL})
    assert r.status_code == 200 and "6-digit code" in r.json()["detail"]
    assert len(outbox) == 1 and outbox[0]["to"] == EMAIL and "password reset code" in outbox[0]["subject"]
    code = code_from(outbox[0])
    r = await client.post("/api/auth/password-reset/confirm", json={"email": EMAIL, "code": code, "new_password": NEW})
    assert r.status_code == 200
    assert (await login(client, OLD)).status_code == 401
    assert (await login(client, NEW)).status_code == 200
    user = await storage_service.get_user_by_email(EMAIL)
    assert user.email_verified is True                      # the code proved the address is theirs
    # the code cannot be used twice
    r = await client.post("/api/auth/password-reset/confirm", json={"email": EMAIL, "code": code, "new_password": OLD})
    assert r.status_code == 400


async def test_unknown_email_gets_the_same_reply_and_no_email(client, outbox):
    r = await client.post("/api/auth/password-reset/request", json={"email": "nobody@example.com"})
    assert r.status_code == 200 and r.json()["detail"] == main.RESET_SENT
    assert outbox == []


async def test_wrong_code_is_counted_and_locks_after_five(client, account, outbox):
    await client.post("/api/auth/password-reset/request", json={"email": EMAIL})
    good = code_from(outbox[0])
    wrong = "000000" if good != "000000" else "111111"
    for _ in range(ev.MAX_ATTEMPTS):
        r = await client.post("/api/auth/password-reset/confirm", json={"email": EMAIL, "code": wrong, "new_password": NEW})
        assert r.status_code == 400
    r = await client.post("/api/auth/password-reset/confirm", json={"email": EMAIL, "code": good, "new_password": NEW})
    assert r.status_code == 429                                # locked: even the right code is refused now
    assert (await login(client, OLD)).status_code == 200


async def test_expired_code_is_refused(client, account, outbox):
    await client.post("/api/auth/password-reset/request", json={"email": EMAIL})
    user = await storage_service.get_user_by_email(EMAIL)
    state = dict(user.password_reset)
    state["expires_at"] -= timedelta(minutes=16)
    await storage_service.users.update_one({"email": EMAIL}, {"$set": {"password_reset": state}})
    r = await client.post("/api/auth/password-reset/confirm",
                          json={"email": EMAIL, "code": code_from(outbox[0]), "new_password": NEW})
    assert r.status_code == 400 and "expired" in r.json()["detail"]


async def test_one_code_a_minute(client, account, outbox):
    await client.post("/api/auth/password-reset/request", json={"email": EMAIL})
    await client.post("/api/auth/password-reset/request", json={"email": EMAIL})
    assert len(outbox) == 1


async def test_verification_code_cannot_reset_the_password(client, account, outbox):
    headers = {"Authorization": f"Bearer {create_access_token({'sub': EMAIL})}"}
    await client.post("/api/notifications/email/verification", headers=headers)
    code = code_from(outbox[0])
    r = await client.post("/api/auth/password-reset/confirm", json={"email": EMAIL, "code": code, "new_password": NEW})
    assert r.status_code == 400
    assert (await login(client, OLD)).status_code == 200


async def test_new_password_signs_out_old_sessions(client, account, outbox):
    old_token = (await login(client, OLD)).json()["access_token"]
    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    assert me.status_code == 200
    await client.post("/api/auth/password-reset/request", json={"email": EMAIL})
    time.sleep(0.01)
    await client.post("/api/auth/password-reset/confirm",
                      json={"email": EMAIL, "code": code_from(outbox[0]), "new_password": NEW})
    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    assert me.status_code == 401 and "password was changed" in me.json()["detail"]
    time.sleep(0.01)
    new_token = (await login(client, NEW)).json()["access_token"]
    assert (await client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_token}"})).status_code == 200


async def test_new_password_must_be_8_to_72_characters(client, account, outbox):
    await client.post("/api/auth/password-reset/request", json={"email": EMAIL})
    r = await client.post("/api/auth/password-reset/confirm",
                          json={"email": EMAIL, "code": code_from(outbox[0]), "new_password": "short"})
    assert r.status_code == 422
