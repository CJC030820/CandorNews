"""Search across all stored articles, and followed publishers saved per account."""
from datetime import datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app import main
from app.core.security import create_access_token
from app.models.user import UserCreate
from app.services.storage import storage_service
from tests.test_api_contracts import article_data


@pytest.fixture
async def api():
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as client:
        yield client


@pytest.fixture
async def headers():
    await storage_service.create_user(UserCreate(name="R", email="search@example.com", password="Test-password-123"))
    return {"Authorization": f"Bearer {create_access_token({'sub': 'search@example.com'})}"}


async def add(title, source="New Straits Times", days_ago=0, **kw):
    await storage_service.create_article(article_data(
        title=title, source=source, url=f"https://example.com/{abs(hash(title))}",
        published_date=datetime(2026, 11, 19) - timedelta(days=days_ago), **kw))


async def test_search_finds_old_articles_beyond_latest_batch(api, headers):
    await add("Old flood relief story", days_ago=200)
    for i in range(5):
        await add(f"Recent market update {i}")
    data = (await api.get("/api/articles/search", params={"q": "flood relief"}, headers=headers)).json()
    assert [a["title"] for a in data["articles"]] == ["Old flood relief story"]


async def test_search_matches_every_word_and_publisher_and_is_literal(api, headers):
    await add("Budget passed", source="Free Malaysia Today")
    await add("Budget delayed", source="Bernama")
    found = (await api.get("/api/articles/search", params={"q": "budget bernama"}, headers=headers)).json()["articles"]
    assert [a["title"] for a in found] == ["Budget delayed"]
    assert (await api.get("/api/articles/search", params={"q": ".*"}, headers=headers)).json()["articles"] == []


async def test_search_needs_login_and_two_characters(api, headers):
    assert (await api.get("/api/articles/search", params={"q": "budget"})).status_code == 401
    assert (await api.get("/api/articles/search", params={"q": "b"}, headers=headers)).status_code == 422


async def test_followed_platforms_saved_to_account(api, headers):
    assert (await api.get("/api/auth/me", headers=headers)).json()["followed_platforms"] is None
    saved = await api.put("/api/users/platforms", json={"platform_ids": ["nst", "fmt", "nst"]}, headers=headers)
    assert saved.json()["followed_platforms"] == ["nst", "fmt"]
    assert (await api.get("/api/auth/me", headers=headers)).json()["followed_platforms"] == ["nst", "fmt"]


@pytest.mark.parametrize("ids", [[], ["unknown"], ["nst", "nst", "fmt", "bernama", "x"]])
async def test_followed_platforms_validation(api, headers, ids):
    assert (await api.put("/api/users/platforms", json={"platform_ids": ids}, headers=headers)).status_code == 422


def test_digest_uses_followed_publishers():
    class A:
        def __init__(self, source): self.source = source
    items = [A("Bernama"), A("New Straits Times"), A("BERNAMA - English Version")]
    assert [a.source for a in main.from_followed(items, ["bernama"])] == ["Bernama", "BERNAMA - English Version"]
    assert len(main.from_followed(items, None)) == 3
