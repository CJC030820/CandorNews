"""API and security contracts, using an isolated database and no app lifespan."""
from datetime import datetime, timedelta

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app import main
from app.core.security import create_access_token
from app.models.article import ArticleCreate
from app.models.user import UserCreate
from app.services.storage import storage_service


@pytest.fixture
async def api():
    # ASGITransport does not run startup: no RSS worker or email scheduler starts.
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as client:
        yield client


@pytest.fixture
async def reader_headers():
    await storage_service.create_user(UserCreate(
        name="API Reader", email="api-reader@example.com", password="Test-password-123"
    ))
    token = create_access_token({"sub": "api-reader@example.com"})
    return {"Authorization": f"Bearer {token}"}


def article_data(**updates):
    data = dict(
        title="Council publishes transport meeting agenda", source="Example News",
        url="https://example.com/agenda", published_date=datetime(2026, 11, 1, 9),
        description="The meeting is scheduled for Monday.", topic="Politics",
        topics=["Politics"], sentiment="Neutral", trust_score=35,
        processing_status="completed",
    )
    data.update(updates)
    return ArticleCreate(**data)


async def test_empty_feed_has_stable_json_contract(api, reader_headers, monkeypatch):
    monkeypatch.setattr(main.news_worker, "last_run_stats", {})
    response = await api.get("/api/articles/feed", headers=reader_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "articles": [], "total_articles_in_db": 0, "last_fetch_run": None,
    }


@pytest.mark.parametrize("method,path,body", [
    ("GET", "/api/auth/me", None),
    ("GET", "/api/articles/feed", None),
    ("GET", "/api/articles/000000000000000000000000", None),
    ("GET", "/api/articles/refresh/nonexistent", None),
    ("POST", "/api/articles/refresh", {"platforms": ["Bernama"]}),
    ("PUT", "/api/users/preferences", {"preferred_topics": ["Sports"]}),
    ("PUT", "/api/users/profile", {"name": "Other"}),
    ("DELETE", "/api/users/me", {"password": "Test-password-123"}),
    ("GET", "/api/notifications/email/status", None),
    ("PUT", "/api/notifications/email", {"email_notifications_enabled": True}),
    ("POST", "/api/notifications/email/test", {}),
])
async def test_protected_routes_require_authentication(api, method, path, body):
    response = await api.request(method, path, json=body)
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.parametrize("token_kind", ["expired", "wrong-signature", "missing-subject", "unknown-user"])
async def test_invalid_token_cannot_read_feed(api, reader_headers, token_kind):
    payload = {"sub": "api-reader@example.com"}
    if token_kind == "expired":
        token = create_access_token(payload, expires_delta=timedelta(seconds=-60))
    elif token_kind == "wrong-signature":
        token = jwt.encode(payload, "test-only-unrelated-signing-key", algorithm=main.ALGORITHM)
    elif token_kind == "missing-subject":
        token = create_access_token({"role": "reader"})
    else:
        token = create_access_token({"sub": "absent@example.com"})
    assert (await api.get("/api/articles/feed", headers={"Authorization": f"Bearer {token}"})).status_code == 401


@pytest.mark.parametrize("limit", [0, -1, 1001, "not-a-number", "1.5"])
async def test_feed_rejects_invalid_limits(api, reader_headers, limit):
    response = await api.get("/api/articles/feed", headers=reader_headers, params={"limit": limit})
    assert response.status_code == 422


async def test_feed_filters_secondary_topics_sorts_and_limits(api, reader_headers):
    oldest = await storage_service.create_article(article_data())
    latest = await storage_service.create_article(article_data(
        url="https://example.com/tech", topic="Technology", topics=["Technology", "Politics"],
        published_date=datetime(2026, 11, 2),
    ))
    await storage_service.create_article(article_data(
        url="https://example.com/sports", topic="Sports", topics=["Sports"],
        published_date=datetime(2026, 11, 3),
    ))
    await storage_service.create_article(article_data(
        url="https://example.com/pending", processing_status="pending",
        published_date=datetime(2026, 11, 4),
    ))
    response = await api.get("/api/articles/feed", headers=reader_headers, params={"topic": "Politics", "limit": 2})
    assert response.status_code == 200
    assert [a["id"] for a in response.json()["articles"]] == [latest.id, oldest.id]
    # This field is a global stored count, not the filtered result count.
    assert response.json()["total_articles_in_db"] == 4
    limited = await api.get("/api/articles/feed", headers=reader_headers, params={"topic": "Politics", "limit": 1})
    assert [a["id"] for a in limited.json()["articles"]] == [latest.id]


@pytest.mark.parametrize("status", ["pending", "failed"])
async def test_unprocessed_article_is_not_public(api, reader_headers, status):
    saved = await storage_service.create_article(article_data(processing_status=status))
    assert (await api.get(f"/api/articles/{saved.id}", headers=reader_headers)).status_code == 404
    assert (await api.get("/api/articles/feed", headers=reader_headers)).json()["articles"] == []


async def test_missing_valid_object_id_returns_not_found(api, reader_headers):
    response = await api.get(f"/api/articles/{ObjectId()}", headers=reader_headers)
    assert response.status_code == 404
    assert response.json() == {"detail": "Article not found"}


@pytest.mark.parametrize("payload", [
    {"email": {"$ne": None}, "password": "anything"},
    {"email": "api-reader@example.com", "password": {"$ne": None}},
])
async def test_login_rejects_nosql_operator_objects(api, reader_headers, payload):
    assert (await api.post("/api/auth/login", json=payload)).status_code == 422


async def test_sql_style_payload_is_not_authentication(api, reader_headers):
    response = await api.post("/api/auth/login", json={"email": "' OR 1=1 --", "password": "anything"})
    assert response.status_code == 401
    assert "access_token" not in response.json()


async def test_topic_operator_string_is_literal(api, reader_headers):
    await storage_service.create_article(article_data())
    response = await api.get("/api/articles/feed", headers=reader_headers, params={"topic": '{"$ne":null}'})
    assert response.status_code == 200
    assert response.json()["articles"] == []


async def test_account_responses_never_expose_password_hash(api, reader_headers):
    response = await api.get("/api/auth/me", headers=reader_headers)
    assert response.status_code == 200
    assert set(response.json()) == {
        "id", "email", "name", "preferred_topics", "email_notifications_enabled", "email_notification_schedule", "email_notification_times", "email_verified",
    }
    assert "password" not in response.text and "hashed_password" not in response.text


async def test_profile_update_only_changes_authenticated_user(api, reader_headers):
    other = await storage_service.create_user(UserCreate(
        name="Other Reader", email="other-reader@example.com", password="Another-password-123"
    ))
    response = await api.put("/api/users/profile", headers=reader_headers, json={
        "name": "Renamed", "email": other.email, "id": other.id,
    })
    assert response.status_code == 200
    assert response.json()["email"] == "api-reader@example.com"
    assert (await storage_service.get_user_by_email(other.email)).name == "Other Reader"


@pytest.mark.parametrize("password", ["a" * 73, "\u754c" * 25])
async def test_registration_rejects_passwords_exceeding_bcrypt_byte_limit(api, password):
    response = await api.post("/api/auth/register", json={
        "name": "Reader", "email": "long-password@example.com", "password": password,
    })
    assert response.status_code == 422
    assert await storage_service.users.count_documents({}) == 0


async def test_refresh_without_platforms_does_not_start_work(api, reader_headers, monkeypatch):
    from unittest.mock import AsyncMock
    worker = AsyncMock()
    monkeypatch.setattr(main.news_worker, "fetch_and_process_news", worker)
    response = await api.post("/api/articles/refresh", headers=reader_headers, json={"platforms": []})
    assert response.status_code == 400
    worker.assert_not_called()


@pytest.mark.xfail(strict=True, reason="SEC-01: JWT subject is a reusable email; old tokens revive after re-registration")
async def test_deleted_account_token_stays_invalid_after_email_reuse(api, reader_headers):
    response = await api.request("DELETE", "/api/users/me", headers=reader_headers,
                                 json={"password": "Test-password-123"})
    assert response.status_code == 200
    assert (await api.get("/api/auth/me", headers=reader_headers)).status_code == 401
    response = await api.post("/api/auth/register", json={
        "name": "New Account", "email": "api-reader@example.com", "password": "New-password-456",
    })
    assert response.status_code == 200
    # Desired security contract. Currently returns 200 with the new account.
    assert (await api.get("/api/auth/me", headers=reader_headers)).status_code == 401
