"""Custom email delivery times (up to three per user)."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient

from app import main
from app.core.security import create_access_token
from app.models.user import UserCreate
from app.services.notification_times import due_times, normalize_times, user_times
from app.services.storage import storage_service

MYT = ZoneInfo("Asia/Kuala_Lumpur")


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def auth():
    await storage_service.create_user(UserCreate(name="Times", email="times@example.com", password="Test-password-123"))
    return {"Authorization": f"Bearer {create_access_token({'sub': 'times@example.com'})}"}


def test_normalize_sorts_and_dedupes():
    assert normalize_times(["19:30", " 07:05", "19:30"]) == ["07:05", "19:30"]


@pytest.mark.parametrize("values", [[], ["7:00"], ["24:00"], ["12:60"], ["noon"], ["01:00", "02:00", "03:00", "04:00"]])
def test_normalize_rejects_bad_or_too_many(values):
    with pytest.raises(ValueError):
        normalize_times(values)


@pytest.mark.parametrize("schedule,expected", [("morning", ["07:00"]), ("night", ["19:00"]), ("both", ["07:00", "19:00"]), (None, ["07:00"])])
def test_legacy_presets_still_work(schedule, expected):
    assert user_times(SimpleNamespace(email_notification_times=[], email_notification_schedule=schedule)) == expected


def test_custom_times_override_preset():
    user = SimpleNamespace(email_notification_times=["12:15"], email_notification_schedule="both")
    assert user_times(user) == ["12:15"]


def _user(times, sent=None):
    return SimpleNamespace(email_notification_times=times, email_notification_schedule="morning", email_notification_last_sent=sent or {})


def test_due_window_and_once_per_day():
    now = datetime(2026, 11, 18, 12, 17, tzinfo=MYT)
    assert due_times(_user(["12:15", "18:00"]), now) == ["12:15"]
    assert due_times(_user(["12:15"], {"12:15": "2026-11-18"}), now) == []
    assert due_times(_user(["12:15"], {"12:15": "2026-11-17"}), now) == ["12:15"]
    assert due_times(_user(["12:00"]), now) == []      # more than 10 minutes ago
    assert due_times(_user(["12:30"]), now) == []      # not yet


async def test_api_saves_up_to_three_times(client, auth):
    r = await client.put("/api/notifications/email", headers=auth, json={"email_notification_times": ["21:00", "06:30", "12:00"]})
    assert r.status_code == 200 and r.json()["email_notification_times"] == ["06:30", "12:00", "21:00"]
    status = (await client.get("/api/notifications/email/status", headers=auth)).json()
    assert status["email_notification_times"] == ["06:30", "12:00", "21:00"]
    assert status["max_notification_times"] == 3 and status["timezone"] == "Asia/Kuala_Lumpur"


@pytest.mark.parametrize("times", [["01:00", "02:00", "03:00", "04:00"], [], ["25:00"]])
async def test_api_rejects_invalid_times_with_readable_message(client, auth, times):
    r = await client.put("/api/notifications/email", headers=auth, json={"email_notification_times": times})
    assert r.status_code == 400 and isinstance(r.json()["detail"], str)


async def test_new_account_defaults_to_seven_am(client):
    r = await client.post("/api/auth/register", json={"name": "New", "email": "new-times@example.com", "password": "Test-password-123"})
    assert r.json()["email_notification_times"] == ["07:00"]


async def test_due_job_sends_once_per_slot(client, auth, monkeypatch):
    await client.put("/api/notifications/email", headers=auth, json={"email_notifications_enabled": True, "email_notification_times": ["12:15", "20:00"]})
    send = Mock(return_value={"success": True, "message": "ok"})
    monkeypatch.setattr(main.email_service, "send_email", send)
    monkeypatch.setattr(main, "_refresh_news_if_stale", AsyncMock())
    now = datetime(2026, 11, 18, 12, 16, tzinfo=MYT)
    assert await main._run_due_email_notifications(now) == 1
    assert await main._run_due_email_notifications(now.replace(minute=18)) == 0   # already sent today
    assert await main._run_due_email_notifications(now.replace(hour=15)) == 0     # no slot due
    assert await main._run_due_email_notifications(now.replace(hour=20, minute=1)) == 1
    assert send.call_count == 2
    user = await storage_service.get_user_by_email("times@example.com")
    assert user.email_notification_last_sent == {"12:15": "2026-11-18", "20:00": "2026-11-18"}


async def test_due_job_skips_disabled_users_and_retries_after_failure(client, auth, monkeypatch):
    await client.put("/api/notifications/email", headers=auth, json={"email_notifications_enabled": False, "email_notification_times": ["09:00"]})
    send = Mock(return_value={"success": False, "message": "SMTP down"})
    monkeypatch.setattr(main.email_service, "send_email", send)
    monkeypatch.setattr(main, "_refresh_news_if_stale", AsyncMock())
    now = datetime(2026, 11, 18, 9, 0, tzinfo=MYT)
    assert await main._run_due_email_notifications(now) == 0 and send.call_count == 0
    await client.put("/api/notifications/email", headers=auth, json={"email_notifications_enabled": True})
    assert await main._run_due_email_notifications(now) == 0 and send.call_count == 1   # failed: not marked sent
    send.return_value = {"success": True, "message": "ok"}
    assert await main._run_due_email_notifications(now.replace(minute=1)) == 1           # retried next minute
