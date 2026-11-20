"""Feed caching, query indexes and skipping unchanged trust-score writes."""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app import main
from app.core.security import create_access_token
from app.models.user import UserCreate
from app.services.storage import storage_service
from app.services.trust_scorer import TrustScorerService
from app.worker import NewsWorker
from tests.test_api_contracts import article_data


@pytest.fixture
async def api():
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as client:
        yield client


@pytest.fixture
async def headers():
    await storage_service.create_user(UserCreate(name="R", email="p@example.com", password="Test-password-123"))
    return {"Authorization": f"Bearer {create_access_token({'sub': 'p@example.com'})}"}


async def add(i, **kw):
    return await storage_service.create_article(article_data(title=f"Story {i}", url=f"https://example.com/p{i}",
                                                             published_date=datetime(2026, 11, 19) - timedelta(hours=i), **kw))


async def test_unchanged_feed_answers_not_modified(api, headers):
    await add(1)
    first = await api.get("/api/articles/feed", params={"limit": 500}, headers=headers)
    assert first.status_code == 200 and first.headers["etag"]
    again = await api.get("/api/articles/feed", params={"limit": 500},
                          headers={**headers, "If-None-Match": first.headers["etag"]})
    assert again.status_code == 304 and again.content == b""


async def test_feed_updates_as_soon_as_articles_change(api, headers):
    a = await add(1)
    first = (await api.get("/api/articles/feed", headers=headers))
    await add(2)
    second = await api.get("/api/articles/feed", headers={**headers, "If-None-Match": first.headers["etag"]})
    assert second.status_code == 200 and len(second.json()["articles"]) == 2
    await storage_service.update_article_fields(a.id, {"title": "Story 1 (updated)"})
    third = await api.get("/api/articles/feed", headers={**headers, "If-None-Match": second.headers["etag"]})
    assert third.status_code == 200


async def test_feed_list_is_light_but_detail_has_full_analysis(api, headers):
    data = article_data(title="Full analysis", url="https://example.com/full")
    saved = await storage_service.create_article(data)
    item = (await api.get("/api/articles/feed", headers=headers)).json()["articles"][0]
    assert "relatedReports" not in item and "trustExplanation" not in item
    assert {"id", "title", "source", "trustScore", "trustLabel", "categories", "image", "date"} <= set(item)
    detail = (await api.get(f"/api/articles/{saved.id}", headers=headers)).json()
    assert "relatedReports" in detail and "trustExplanation" in detail


async def test_query_indexes_exist():
    await storage_service.ensure_indexes()
    keys = [list(ix["key"]) for ix in (await storage_service.articles.index_information()).values()]
    assert [("processing_status", 1), ("published_date", -1)] in keys
    assert [("keywords", 1), ("published_date", -1)] in keys


async def test_rescore_skips_articles_whose_score_did_not_change(monkeypatch):
    scorer = TrustScorerService()
    for i in range(3):
        data = article_data(title=f"Rescore {i}", url=f"https://example.com/r{i}")
        saved = await storage_service.create_article(data)
        result = await scorer.calculate_trust_score(saved.dict(), [])
        await storage_service.update_article_fields(saved.id, result)
    worker = NewsWorker()
    writes = AsyncMock(wraps=storage_service.update_article_fields)
    monkeypatch.setattr(storage_service, "update_article_fields", writes)
    assert await worker.rescore_recent_articles() == 3
    assert writes.await_count == 0 and worker.last_rescore_changed == 0
