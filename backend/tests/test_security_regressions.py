"""Open security defects, isolated from networks and SMTP.

SEC-01 to SEC-04 are fixed; these tests keep them fixed.
"""
import logging
from unittest.mock import Mock

import pytest
import requests
from httpx import ASGITransport, AsyncClient

from app import main
from app.services.news_fetcher import NewsFetcherService


# SEC-02 fixed: the page lookup only requests public addresses (redirects included).
def test_rss_image_fallback_does_not_request_loopback(monkeypatch):
    feed_url = "https://publisher.example/feed"
    private_url = "http://127.0.0.1:8080/internal"
    feed_response = Mock()
    feed_response.content = (
        '<rss version="2.0"><channel><title>Example News</title><item>'
        '<title>Council publishes its meeting agenda</title>'
        f'<link>{private_url}</link><description>Agenda published.</description>'
        '</item></channel></rss>'
    ).encode()
    page_response = Mock(status_code=200, text="<html></html>")

    # Every GET is intercepted, including the undesirable localhost request.
    get = Mock(side_effect=lambda url, **kwargs: (
        feed_response if url == feed_url else page_response
    ))
    monkeypatch.setattr("app.services.news_fetcher.requests.get", get)

    NewsFetcherService().fetch_from_rss(feed_url)

    assert get.call_args_list[0].args[0] == feed_url
    assert all(call.args[0] != private_url for call in get.call_args_list)


# SEC-04 fixed: credential values in URLs are redacted before logging.
def test_provider_retry_redacts_query_credentials(monkeypatch, caplog):
    fake_secret = "FAKE-TEST-KEY-DO-NOT-USE"
    response = requests.Response()
    response.status_code = 401
    response.reason = "Unauthorized"
    response.url = f"https://provider.example/headlines?apiKey={fake_secret}"
    get = Mock(return_value=response)
    monkeypatch.setattr("app.services.news_fetcher.requests.get", get)
    sleep = Mock()
    monkeypatch.setattr("app.services.news_fetcher.time.sleep", sleep)

    with caplog.at_level(logging.WARNING, logger="app.services.news_fetcher"):
        with pytest.raises(requests.HTTPError):
            NewsFetcherService()._make_request_with_retry(
                "https://provider.example/headlines", {"apiKey": fake_secret},
                max_retries=1,
            )

    assert get.call_count == 2
    assert sleep.call_count == 1
    assert caplog.records, "A sanitized provider failure should still be logged"
    assert fake_secret not in caplog.text


# SEC-03 fixed: digests require a verified address (see test_email_verification.py).
async def test_unverified_account_cannot_send_digest(monkeypatch):
    send = Mock(return_value={"success": True, "message": "Mock delivery only"})
    monkeypatch.setattr(main.email_service, "send_email", send)
    # ASGITransport does not start the RSS worker or scheduled email jobs.
    async with AsyncClient(
        transport=ASGITransport(app=main.app), base_url="http://test"
    ) as client:
        credentials = {"email": "unverified@example.com", "password": "Test-password-123"}
        registered = await client.post(
            "/api/auth/register", json={**credentials, "name": "Unverified Reader"}
        )
        registered.raise_for_status()
        login = await client.post("/api/auth/login", json=credentials)
        login.raise_for_status()
        response = await client.post(
            "/api/notifications/email/test",
            headers={"Authorization": f"Bearer {login.json()['access_token']}"},
            json={"message": "Synthetic security regression message"},
        )

    assert response.status_code == 403, "Sending must require verified address ownership"
    send.assert_not_called()


def test_page_lookup_refuses_redirect_to_private_address(monkeypatch):
    from app.services import news_fetcher
    monkeypatch.setattr("app.services.image_cache.is_public_http_url", lambda url: "127.0.0.1" not in url)
    redirect = Mock(status_code=302, headers={"Location": "http://127.0.0.1/admin"})
    get = Mock(return_value=redirect)
    monkeypatch.setattr("app.services.news_fetcher.requests.get", get)
    assert news_fetcher.NewsFetcherService()._fetch_og_image("https://publisher.example/story") is None
    assert [c.args[0] for c in get.call_args_list] == ["https://publisher.example/story"]


def test_redact_hides_credentials():
    from app.services.news_fetcher import _redact
    text = _redact("401 for url: https://x.example/a?q=1&apiKey=SECRET1&token=SECRET2")
    assert "SECRET" not in text and "q=1" in text and "apiKey=***" in text
