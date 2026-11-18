"""Images are always available: Bernama address fix, retries, CA bundle, self-repair."""
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
import requests
from httpx import ASGITransport, AsyncClient

from app import main
from app.core.security import create_access_token
from app.models.user import UserCreate
from app.services import image_cache
from app.services.storage import storage_service
from app.worker import NewsWorker
from tests.test_api_contracts import article_data

BERNAMA = "https://www.bernama.com/storage/photos/abc123-medium"


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(image_cache, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(image_cache, "is_public_http_url", lambda url: True)
    return tmp_path


def _image(body=b"img", status=200, content_type="image/webp"):
    r = Mock(status_code=status, headers={"Content-Type": content_type}, is_redirect=False, is_permanent_redirect=False)
    r.iter_content.return_value = [body]
    r.__enter__ = Mock(return_value=r)
    r.__exit__ = Mock(return_value=False)
    return r


def test_bernama_images_try_the_working_server_first():
    assert image_cache.source_candidates(BERNAMA) == [
        "https://web14.bernama.com/storage/photos/abc123-medium",
        "https://web14.bernama.com/storage/photos/abc123",
        BERNAMA,
    ]
    other = "https://storage.googleapis.com/nst/x.jpg"
    assert image_cache.source_candidates(other) == [other]


def test_bernama_copy_is_stored_under_the_article_image_url(cache_dir, monkeypatch):
    calls = []

    def fake_get(url, **kw):
        calls.append(url)
        return _image(b"webp") if "web14" in url else _image(status=404, content_type="text/html")
    monkeypatch.setattr(image_cache.requests, "get", fake_get)
    assert image_cache.download(BERNAMA) is True
    assert calls[0].startswith("https://web14.bernama.com/")
    path, content_type = image_cache.cached(BERNAMA)
    assert path.read_bytes() == b"webp" and content_type == "image/webp"


def test_timeout_is_retried_then_other_address_used(cache_dir, monkeypatch):
    calls = []

    def fake_get(url, **kw):
        calls.append(url)
        if url.endswith("-medium") and "web14" in url:
            raise requests.ConnectTimeout("slow")
        return _image()
    monkeypatch.setattr(image_cache.requests, "get", fake_get)
    assert image_cache.download(BERNAMA) is True
    assert calls[:3] == ["https://web14.bernama.com/storage/photos/abc123-medium"] * 2 + ["https://web14.bernama.com/storage/photos/abc123"]


def test_downloads_verify_certificates_with_the_extra_intermediate(cache_dir, monkeypatch):
    seen = {}

    def fake_get(url, **kw):
        seen.update(kw)
        return _image()
    monkeypatch.setattr(image_cache.requests, "get", fake_get)
    image_cache.download("https://example.com/a.jpg")
    assert seen["verify"] == image_cache.CA_BUNDLE and seen["verify"] is not False
    bundle = Path(image_cache.CA_BUNDLE).read_text(encoding="utf-8")
    assert "Sectigo Public Server Authentication CA DV R36" in bundle
    assert bundle.count("BEGIN CERTIFICATE") > 100          # full standard root store kept


async def test_feed_reports_when_a_stored_copy_exists(cache_dir, monkeypatch):
    await storage_service.create_user(UserCreate(name="Img", email="img@example.com", password="Test-password-123"))
    stored = await storage_service.create_article(article_data(url="https://example.com/a", image_url="https://example.com/a.jpg"))
    await storage_service.create_article(article_data(url="https://example.com/b", image_url="https://example.com/b.jpg"))
    monkeypatch.setattr(image_cache.requests, "get", lambda url, **kw: _image())
    assert image_cache.download("https://example.com/a.jpg")
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as client:
        feed = (await client.get("/api/articles/feed", headers={"Authorization": f"Bearer {create_access_token({'sub': 'img@example.com'})}"})).json()
    flags = {a["id"]: a["imageStored"] for a in feed["articles"]}
    assert flags[stored.id] is True and list(flags.values()).count(False) == 1


async def test_collection_repairs_missing_images_of_recent_articles(cache_dir, monkeypatch):
    await storage_service.create_article(article_data(url="https://example.com/old", image_url=BERNAMA))
    worker = NewsWorker()
    monkeypatch.setattr(worker.news_fetcher, "fetch_all_sources", Mock(return_value=[]))
    monkeypatch.setattr(worker, "rescore_recent_articles", AsyncMock(return_value=0))
    monkeypatch.setattr(image_cache.requests, "get", lambda url, **kw: _image() if "web14" in url else _image(status=404, content_type="text/html"))
    stats = await worker.fetch_and_process_news()
    assert stats["images_backfilled"] == 1
    assert image_cache.cached(BERNAMA) is not None
