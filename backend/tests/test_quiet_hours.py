"""Automatic news collection pauses overnight (12am-6am Malaysia time)."""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock
import pytest
import app.main as main
from app.worker import NewsWorker, in_quiet_hours

MYT = timezone(timedelta(hours=8))


@pytest.mark.parametrize("hour,minute,quiet", [
    (23, 59, False), (0, 0, True), (3, 30, True), (5, 59, True), (6, 0, False), (12, 0, False)])
def test_quiet_hours_follow_malaysia_time(hour, minute, quiet):
    assert in_quiet_hours(datetime(2026, 11, 22, hour, minute, tzinfo=MYT)) is quiet


def test_utc_time_is_converted_to_malaysia_time():
    # 17:00 UTC is 1am in Malaysia; 23:00 UTC is 7am.
    assert in_quiet_hours(datetime(2026, 11, 22, 17, 0, tzinfo=timezone.utc))
    assert not in_quiet_hours(datetime(2026, 11, 22, 23, 0, tzinfo=timezone.utc))


async def test_scheduled_run_is_skipped_overnight(monkeypatch):
    worker = NewsWorker()
    worker.fetch_and_process_news = AsyncMock(return_value={"saved": 1})
    monkeypatch.setattr("app.worker.in_quiet_hours", lambda now=None: True)
    assert await worker.scheduled_fetch() is None
    worker.fetch_and_process_news.assert_not_called()
    monkeypatch.setattr("app.worker.in_quiet_hours", lambda now=None: False)
    assert await worker.scheduled_fetch() == {"saved": 1}


async def test_no_refresh_before_overnight_digests(monkeypatch):
    fetch = AsyncMock(return_value={})
    monkeypatch.setattr(main.news_worker, "fetch_and_process_news", fetch)
    monkeypatch.setattr(main.news_worker, "last_run_at", None)
    monkeypatch.setattr("app.worker.in_quiet_hours", lambda now=None: True)
    await main._refresh_news_if_stale()
    fetch.assert_not_called()
    monkeypatch.setattr("app.worker.in_quiet_hours", lambda now=None: False)
    await main._refresh_news_if_stale()
    fetch.assert_called_once()
