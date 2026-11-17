"""Stored image copies, trust weight changes and trust wording."""
from unittest.mock import Mock

import pytest
from httpx import ASGITransport, AsyncClient

from app import main
from app.services import email_service, image_cache
from app.services.news_fetcher import NewsFetcherService
from app.services.storage import storage_service
from app.services.trust_scorer import SCORE_VERSION, TrustScorerService, WEIGHTS
from tests.test_api_contracts import article_data


@pytest.fixture
async def api():
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as client:
        yield client


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(image_cache, "CACHE_DIR", tmp_path)
    return tmp_path


def test_weights_give_other_publishers_twenty_percent():
    assert WEIGHTS == {"source_reputation": .50, "corroboration": .20,
                       "metadata_completeness": .15, "sentiment_neutrality": .15}
    assert sum(WEIGHTS.values()) == pytest.approx(1)


async def test_labels_use_trust_wording():
    article = {"title": "Council opens library", "url": "https://www.nst.com.my/a", "author": "A",
               "published_date": "2026-11-17", "source": "NST", "description": "d", "sentiment": "Neutral"}
    result = await TrustScorerService().calculate_trust_score(article)
    assert result["trust_label"].endswith("trust") or result["trust_label"] == "Needs verification"
    assert "indicator" not in result["trust_label"]
    assert result["trust_version"] == SCORE_VERSION


def test_digest_uses_trust_wording():
    digest = email_service.build_news_digest_email("Reader", [{
        "title": "T", "source": "S", "description": "D", "date": "2026-11-17T00:00:00",
        "trustScore": 72, "url": "https://example.com/a"}])
    assert "72/100 trust" in digest["html"]
    assert "Trust: 72/100" in digest["text"]
    assert "indicator" not in digest["html"] + digest["text"]


@pytest.mark.parametrize("url", ["http://127.0.0.1/a.jpg", "http://10.0.0.5/a.jpg", "http://localhost/a.jpg",
                                 "ftp://example.com/a.jpg", "", None])
def test_private_or_non_http_images_are_refused(url, cache_dir):
    assert image_cache.is_public_http_url(url) is False
    assert image_cache.download(url) is False


def _response(status=200, content_type="image/jpeg", body=b"img", location=None):
    response = Mock(status_code=status, headers={"Content-Type": content_type, **({"Location": location} if location else {})},
                    is_redirect=bool(location), is_permanent_redirect=False)
    response.iter_content.return_value = [body]
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    return response


def test_image_is_downloaded_once_and_served_from_cache(cache_dir, monkeypatch):
    monkeypatch.setattr(image_cache, "is_public_http_url", lambda url: True)
    get = Mock(return_value=_response(body=b"jpeg-bytes"))
    monkeypatch.setattr(image_cache.requests, "get", get)
    url = "https://www.bernama.com/storage/photos/abc-medium"
    assert image_cache.download_many([url, url]) == 1
    path, content_type = image_cache.cached(url)
    assert path.read_bytes() == b"jpeg-bytes" and content_type == "image/jpeg"
    assert image_cache.download(url) is True
    assert get.call_count == 1


def test_redirect_to_private_address_is_refused(cache_dir, monkeypatch):
    monkeypatch.setattr(image_cache, "is_public_http_url", lambda url: "127.0.0.1" not in url)
    monkeypatch.setattr(image_cache.requests, "get", Mock(return_value=_response(status=302, location="http://127.0.0.1/x")))
    assert image_cache.download("https://example.com/a.jpg") is False
    assert image_cache.cached("https://example.com/a.jpg") is None


def test_non_image_and_oversized_responses_are_not_stored(cache_dir, monkeypatch):
    monkeypatch.setattr(image_cache, "is_public_http_url", lambda url: True)
    monkeypatch.setattr(image_cache.requests, "get", Mock(return_value=_response(content_type="text/html")))
    assert image_cache.download("https://example.com/page") is False
    monkeypatch.setattr(image_cache, "MAX_BYTES", 2)
    monkeypatch.setattr(image_cache.requests, "get", Mock(return_value=_response(body=b"too-big")))
    assert image_cache.download("https://example.com/big.jpg") is False


async def test_image_route_serves_stored_copy_without_login(api, cache_dir, monkeypatch):
    created = await storage_service.create_article(article_data(image_url="https://www.bernama.com/p/1-medium"))
    monkeypatch.setattr(image_cache, "is_public_http_url", lambda url: True)
    monkeypatch.setattr(image_cache.requests, "get", Mock(return_value=_response(content_type="image/png", body=b"png")))
    response = await api.get(f"/api/articles/{created.id}/image")
    assert response.status_code == 200
    assert response.content == b"png" and response.headers["content-type"] == "image/png"
    assert "max-age" in response.headers["cache-control"]


async def test_image_route_404s_when_unavailable(api, cache_dir, monkeypatch):
    without_image = await storage_service.create_article(article_data(url="https://example.com/no-image"))
    assert (await api.get(f"/api/articles/{without_image.id}/image")).status_code == 404
    blocked = await storage_service.create_article(article_data(url="https://example.com/blocked", image_url="https://www.bernama.com/p/2"))
    monkeypatch.setattr(image_cache, "download", lambda url: False)
    assert (await api.get(f"/api/articles/{blocked.id}/image")).status_code == 404
    assert (await api.get("/api/articles/not-an-id/image")).status_code == 404


def test_known_articles_do_not_reopen_publisher_pages(monkeypatch):
    fetcher = NewsFetcherService()
    feed = Mock(raise_for_status=Mock(), content=b"""<?xml version="1.0"?><rss><channel><title>BERNAMA</title>
        <item><title>Old story</title><link>https://www.bernama.com/old</link></item>
        <item><title>New story</title><link>https://www.bernama.com/new</link></item></channel></rss>""")
    monkeypatch.setattr("app.services.news_fetcher.requests.get", Mock(return_value=feed))
    og = Mock(return_value="https://www.bernama.com/p/new.jpg")
    monkeypatch.setattr(fetcher, "_fetch_og_image", og)
    articles = fetcher.fetch_from_rss("https://www.bernama.com/en/rssfeed.php", {"https://www.bernama.com/old"})
    og.assert_called_once_with("https://www.bernama.com/new")
    assert {a["url"]: a["image"] for a in articles} == {
        "https://www.bernama.com/old": None, "https://www.bernama.com/new": "https://www.bernama.com/p/new.jpg"}
