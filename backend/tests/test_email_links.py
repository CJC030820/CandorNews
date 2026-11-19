"""Digest emails link to the article's page on the CandorNews website."""
from unittest.mock import Mock

import pytest
from httpx import ASGITransport, AsyncClient

from app import main
from app.core.config import Settings
from app.core.security import create_access_token
from app.models.user import UserCreate
from app.services import email_service
from app.services.storage import storage_service
from tests.test_api_contracts import article_data

SITE = "https://candornews.example.test"
ORIGINAL = "https://www.nst.com.my/news/2026/11/original-story"


def _digest(**kw):
    article = {"id": "abc123", "title": "Budget passed", "source": "NST", "description": "Summary",
               "date": "2026-11-18T01:00:00", "trustScore": 70, "url": ORIGINAL}
    return email_service.build_news_digest_email("Reader", [article], site_url=SITE, **kw)


def test_digest_links_to_candornews_article_page_only():
    digest = _digest()
    assert f"{SITE}/article/abc123" in digest["text"]
    assert f'href="{SITE}/article/abc123"' in digest["html"]
    assert ORIGINAL not in digest["text"] and ORIGINAL not in digest["html"]
    assert "Read on CandorNews" in digest["text"] and "Read on CandorNews" in digest["html"]


def test_article_page_url_is_encoded_and_needs_both_parts():
    assert email_service.article_page_url(SITE + "/", "a b/c") == f"{SITE}/article/a%20b%2Fc"
    assert email_service.article_page_url("", "abc") == ""
    assert email_service.article_page_url(SITE, None) == ""


def test_without_site_url_no_link_is_added():
    digest = email_service.build_news_digest_email("Reader", [{"id": "x", "title": "T", "url": ORIGINAL}])
    assert ORIGINAL not in digest["text"] and "href" not in digest["html"].split("Hi Reader")[1].split("You're receiving")[0]


@pytest.mark.parametrize("public,cors,expected", [
    ("", "https://candornews.malaysiawest.cloudapp.azure.com", "https://candornews.malaysiawest.cloudapp.azure.com"),
    ("", "http://localhost:3000,http://127.0.0.1:3000", "http://localhost:3000"),
    ("https://news.example.com/", "http://localhost:3000", "https://news.example.com"),
])
def test_site_url_setting(public, cors, expected):
    assert Settings(PUBLIC_SITE_URL=public, CORS_ORIGINS=cors).site_url == expected


async def test_sent_digest_uses_site_links(monkeypatch):
    await storage_service.create_user(UserCreate(name="Links", email="links@example.com", password="Test-password-123"))
    await storage_service.users.update_one({"email": "links@example.com"}, {"$set": {"email_verified": True}})
    created = await storage_service.create_article(article_data(url=ORIGINAL, title="Budget passed"))
    monkeypatch.setattr(main.settings, "PUBLIC_SITE_URL", SITE)
    send = Mock(return_value={"success": True, "message": "ok"})
    monkeypatch.setattr(main.email_service, "send_email", send)
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as client:
        r = await client.post("/api/notifications/email/test", json={},
                              headers={"Authorization": f"Bearer {create_access_token({'sub': 'links@example.com'})}"})
    assert r.status_code == 200
    text, html = send.call_args.kwargs["body_text"], send.call_args.kwargs["body_html"]
    assert f"{SITE}/article/{created.id}" in text and f"{SITE}/article/{created.id}" in html
    assert ORIGINAL not in text and ORIGINAL not in html


def test_emails_use_site_design():
    from app.services import email_verification
    for html_body in (_digest()["html"], email_verification.build_code_email("Reader", "123456", SITE)["html"]):
        assert "#2563EB" in html_body and f"{SITE}/CandorNews-removebg-preview.png" in html_body
        assert "#667eea" not in html_body.lower() and "#764ba2" not in html_body.lower()
        assert "\U0001F4F0" not in html_body
    assert "\U0001F4F0" not in _digest()["subject"]
    assert f'href="{SITE}/profile"' in _digest()["html"]
