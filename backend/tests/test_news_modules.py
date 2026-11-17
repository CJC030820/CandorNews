"""Offline edge cases for the actual collection and analysis pipeline.

Synthetic inputs verify contracts and regressions, not real-world NLP accuracy.
The shared conftest isolates MongoDB; this file also blocks outbound requests.
"""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
import requests

from app.services import news_fetcher
from app.services.deduplicator import DeduplicatorService
from app.services.news_fetcher import NewsFetcherService
from app.services.sentiment_analyzer import SentimentAnalyzerService
from app.services.storage import storage_service
from app.services.summarizer import SummarizerService
from app.services.trust_scorer import TrustScorerService, related_title
from app.worker import NewsWorker


@pytest.fixture(autouse=True)
def block_outbound_http(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("A module test attempted a real HTTP request")

    monkeypatch.setattr(requests.sessions.Session, "request", blocked)


@pytest.fixture
def fetcher():
    service = NewsFetcherService()
    service.newsapi_key = "synthetic-test-key"
    service.gnews_api_key = "synthetic-test-key"
    return service


@pytest.mark.parametrize("provider,key_attribute", [
    ("fetch_from_newsapi", "newsapi_key"),
    ("fetch_from_gnews", "gnews_api_key"),
])
def test_collection_without_api_key_skips_network(fetcher, monkeypatch, provider, key_attribute):
    setattr(fetcher, key_attribute, "")
    request = Mock()
    monkeypatch.setattr(fetcher, "_make_request_with_retry", request)
    assert getattr(fetcher, provider)() == []
    request.assert_not_called()


@pytest.mark.parametrize("provider", ["fetch_from_newsapi", "fetch_from_gnews"])
@pytest.mark.parametrize("payload", [{"articles": []}, {}])
def test_empty_api_response(fetcher, monkeypatch, provider, payload):
    monkeypatch.setattr(fetcher, "_make_request_with_retry", Mock(return_value=Mock(json=Mock(return_value=payload))))
    assert getattr(fetcher, provider)() == []


@pytest.mark.parametrize("provider", ["fetch_from_newsapi", "fetch_from_gnews"])
@pytest.mark.parametrize("failure", [requests.Timeout("upstream timeout"), requests.HTTPError("429 throttled")])
def test_api_failure_returns_empty_batch(fetcher, monkeypatch, provider, failure):
    monkeypatch.setattr(fetcher, "_make_request_with_retry", Mock(side_effect=failure))
    assert getattr(fetcher, provider)() == []


@pytest.mark.parametrize("provider", ["fetch_from_newsapi", "fetch_from_gnews"])
def test_invalid_api_json_is_handled(fetcher, monkeypatch, provider):
    response = Mock(json=Mock(side_effect=ValueError("invalid JSON")))
    monkeypatch.setattr(fetcher, "_make_request_with_retry", Mock(return_value=response))
    assert getattr(fetcher, provider)() == []


@pytest.mark.parametrize("provider", ["fetch_from_newsapi", "fetch_from_gnews"])
def test_api_normalizes_optional_fields_and_html(fetcher, monkeypatch, provider):
    article = {"title": "<b>City</b>&nbsp;opens library", "source": {"name": "Example News"},
               "url": "https://example.test/library", "description": "Books &amp; archives"}
    response = Mock(json=Mock(return_value={"articles": [article]}))
    monkeypatch.setattr(fetcher, "_make_request_with_retry", Mock(return_value=response))
    result, = getattr(fetcher, provider)()
    assert result["title"] == "City opens library"
    assert result["description"] == "Books & archives"
    assert result["source"] == "Example News"
    assert result["author"] is None and result["published_at"] is None
    assert result["content"] == ""


def test_request_retry_recovers_with_bounded_timeout(fetcher, monkeypatch):
    response = Mock()
    request = Mock(side_effect=[requests.Timeout("slow"), response])
    sleep = Mock()
    monkeypatch.setattr(news_fetcher.requests, "get", request)
    monkeypatch.setattr(news_fetcher.time, "sleep", sleep)
    assert fetcher._make_request_with_retry("https://example.test/feed", {"q": "news"}) is response
    assert request.call_args_list == [call("https://example.test/feed", params={"q": "news"}, timeout=10)] * 2
    response.raise_for_status.assert_called_once_with()
    sleep.assert_called_once_with(0.5)


def test_request_retry_exhaustion_is_bounded(fetcher, monkeypatch):
    request = Mock(side_effect=requests.Timeout("slow"))
    sleep = Mock()
    monkeypatch.setattr(news_fetcher.requests, "get", request)
    monkeypatch.setattr(news_fetcher.time, "sleep", sleep)
    with pytest.raises(requests.Timeout):
        fetcher._make_request_with_retry("https://example.test/feed", {}, max_retries=2)
    assert request.call_count == 3
    assert sleep.call_args_list == [call(0.5), call(1.0)]


@pytest.mark.parametrize("failure", [requests.exceptions.InvalidURL("bad URL"), requests.Timeout("slow RSS"), requests.HTTPError("404")])
def test_rss_request_errors_are_handled(fetcher, monkeypatch, failure):
    monkeypatch.setattr(news_fetcher.requests, "get", Mock(side_effect=failure))
    assert fetcher.fetch_from_rss("https://example.test/feed") == []


@pytest.mark.parametrize("content", [b"", b"<rss><channel><title>Empty feed</title></channel></rss>", b"<html>Publisher unavailable</html>"])
def test_empty_or_non_feed_rss_response(fetcher, monkeypatch, content):
    monkeypatch.setattr(news_fetcher.requests, "get", Mock(return_value=Mock(content=content)))
    assert fetcher.fetch_from_rss("https://example.test/feed") == []


def test_rss_parser_cleans_text_and_resolves_relative_image(fetcher, monkeypatch):
    xml = b'''<?xml version="1.0"?><rss version="2.0"><channel>
      <title>Example News</title><item><title>City &amp; county</title>
      <link>https://example.test/news/library</link>
      <description><![CDATA[<p>Library&nbsp; opens</p><img src="/photo.jpg">]]></description>
      <pubDate>Thu, 12 Nov 2026 08:00:00 +0800</pubDate></item>
    </channel></rss>'''
    request = Mock(return_value=Mock(content=xml))
    fallback = Mock()
    monkeypatch.setattr(news_fetcher.requests, "get", request)
    monkeypatch.setattr(fetcher, "_fetch_og_image", fallback)
    article, = fetcher.fetch_from_rss("https://example.test/feed")
    assert article["title"] == "City & county"
    assert article["description"] == "Library opens"
    assert article["image"] == "https://example.test/photo.jpg"
    assert article["author"] is None
    assert article["published_at"] == "Thu, 12 Nov 2026 08:00:00 +0800"
    assert request.call_args.kwargs["timeout"] == 8
    fallback.assert_not_called()


def test_failed_image_fallback_does_not_drop_rss_article(fetcher, monkeypatch):
    xml = b'''<rss version="2.0"><channel><title>Example News</title>
      <item><title>Library opens</title><link>https://example.test/story</link></item>
    </channel></rss>'''
    monkeypatch.setattr(news_fetcher.requests, "get", Mock(return_value=Mock(content=xml)))
    monkeypatch.setattr(fetcher, "_fetch_og_image", Mock(side_effect=requests.Timeout("image unavailable")))
    article, = fetcher.fetch_from_rss("https://example.test/feed")
    assert article["url"] == "https://example.test/story"
    assert article["image"] is None


@pytest.mark.parametrize("value,expected", [
    ("//cdn.example.test/photo.jpg", "https://cdn.example.test/photo.jpg"),
    ("/photo.jpg?a=1&amp;b=2", "https://example.test/photo.jpg?a=1&b=2"),
    ("javascript:alert(1)", None), ("data:image/png;base64,abc", None),
    ("file:///private/image.png", None), (None, None),
])
def test_rss_image_urls_use_http_schemes(value, expected):
    assert NewsFetcherService._normalize_image_url(value, "https://example.test/story") == expected


def test_platform_selection_avoids_unselected_feeds(fetcher, monkeypatch):
    monkeypatch.setattr(news_fetcher.settings, "RSS_FEEDS", "https://bernama.test/feed,https://nst.test/feed")
    request = Mock(return_value=[{"source": "BERNAMA", "title": "City news"}])
    monkeypatch.setattr(fetcher, "fetch_from_rss", request)
    assert fetcher.fetch_all_sources([" Bernama "]) == [{"source": "BERNAMA", "title": "City news"}]
    request.assert_called_once_with("https://bernama.test/feed", None)


@pytest.mark.parametrize("articles", [[], [{}], [{"title": "Missing URL"}], [{"url": "https://example.test/"}]])
def test_dedup_skips_incomplete_records(articles):
    assert DeduplicatorService().remove_duplicates(articles) == []


def test_similar_titles_merge_only_within_publisher():
    first = {"title": "City council approves library funding", "url": "https://example.test/first"}
    revised = {"title": "City council approves library funding!", "url": "https://www.example.test/revised"}
    other = {**revised, "url": "https://other.test/report"}
    unrelated = {"title": "Football team wins championship", "url": "https://example.test/sports"}
    assert DeduplicatorService().remove_duplicates([first, revised, other, unrelated]) == [first, other, unrelated]


@pytest.mark.xfail(strict=True, raises=ValueError, reason="Known defect: malformed URL aborts dedup before later valid articles are processed")
def test_malformed_article_url_does_not_abort_valid_batch():
    invalid = {"title": "Malformed publisher URL", "url": "https://[invalid"}
    valid = {"title": "City library opens this week", "url": "https://example.test/good"}
    assert DeduplicatorService().remove_duplicates([invalid, valid]) == [valid]


@pytest.fixture(scope="module")
def sentiment():
    return SentimentAnalyzerService()


@pytest.mark.parametrize("compound,expected", [
    (-1.0, "Negative"), (-0.05, "Negative"), (-0.0499, "Neutral"),
    (0.0, "Neutral"), (0.0499, "Neutral"), (0.05, "Positive"), (1.0, "Positive"),
])
def test_sentiment_label_boundary(sentiment, compound, expected):
    assert sentiment.get_sentiment_label({"compound": compound}) == expected


@pytest.mark.parametrize("scores,expected", [
    ({"neu": .70, "pos": .20, "neg": .0, "compound": .45}, "Emotionally Charged"),
    ({"neu": .70, "pos": .0, "neg": .20, "compound": -.45}, "Emotionally Charged"),
    ({"neu": .82, "pos": .12, "neg": .0, "compound": .25}, "Mildly Emotional"),
    ({"neu": .9, "pos": .1, "neg": .0, "compound": .8}, "Neutral / Objective"),
    ({"neu": .7, "pos": .2, "neg": .0, "compound": .24}, "Neutral / Objective"),
    ({}, "Neutral / Objective"),
])
def test_tone_requires_combined_emotional_cues(sentiment, scores, expected):
    assert sentiment.get_tone_label(scores) == expected


def test_empty_article_sentiment_is_neutral(sentiment):
    result = sentiment.analyze_article_sentiment({})
    assert result == {"sentiment": "Neutral", "sentiment_score": 0.0, "tone_label": "Neutral / Objective"}


def test_sentiment_negation_changes_polarity(sentiment):
    assert sentiment.analyze_article_sentiment({"title": "The result is good"})["sentiment"] == "Positive"
    assert sentiment.analyze_article_sentiment({"title": "The result is not good"})["sentiment"] == "Negative"


def test_sentiment_uses_body_when_headline_is_neutral(sentiment):
    result = sentiment.analyze_article_sentiment({"title": "Council publishes report", "content": "A terrible disaster and horrible failure."})
    assert result["sentiment"] == "Negative"
    assert -1.0 <= result["sentiment_score"] < -.05


def test_long_article_summary_is_generated_without_inventing_sentences():
    lead = "The city library opens on Monday. It contains a public archive. Residents can borrow books. The council published opening hours."
    text = lead + " " + "The archive contains books and newspapers for public access. " * 600
    assert len(text.split()) > 5000
    assert SummarizerService().summarize(text) == lead


@pytest.mark.xfail(strict=True, reason="Known limitation: punctuation-only splitting corrupts abbreviations and decimal amounts")
def test_summary_preserves_decimal_amounts_and_abbreviations():
    text = "Dr. Lee announced 3.5 million in funding. Schools will receive grants."
    assert SummarizerService(max_sentences=2).summarize(text) == text


@pytest.mark.parametrize("article,expected", [
    ({}, "No summary available."),
    ({"description": "Publisher description.", "content": "Full article."}, "Publisher description."),
    ({"content_excerpt": "Stored excerpt.", "content": "Full article."}, "Stored excerpt."),
    ({"content": "Full article."}, "Full article."),
])
def test_summary_helper_fallbacks(article, expected):
    assert SummarizerService().summarize_article(article) == expected


@pytest.mark.parametrize("text", [" ", "\n\t", "...!?..."])
def test_summary_without_sentences_is_empty(text):
    assert SummarizerService().summarize(text) == ""


def full_article():
    return {"title": "City council approves new library funding", "url": "https://example.test/story",
            "source": "Example News", "author": "Reporter", "published_date": datetime(2026, 11, 12),
            "description": "The council published details of the library funding.", "sentiment": "Neutral"}


async def test_missing_author_reduces_score_by_metadata_weight():
    scorer = TrustScorerService()
    complete = await scorer.calculate_trust_score(full_article())
    incomplete = await scorer.calculate_trust_score({**full_article(), "author": None})
    assert complete["trust_components"]["metadata_completeness"] == 1.0
    assert incomplete["trust_components"]["metadata_completeness"] == .75
    assert complete["trust_score"] - incomplete["trust_score"] == pytest.approx(3.75)
    for key in ("source_reputation", "corroboration", "sentiment_neutrality"):
        assert incomplete["trust_components"][key] == complete["trust_components"][key]


@pytest.mark.parametrize("configured,expected", [(None, .5), (-20, .0), (0, .0), (80, .8), (100, 1.), (150, 1.)])
def test_reputation_default_and_bounds(configured, expected):
    record = None if configured is None else SimpleNamespace(credibility_score=configured)
    assert TrustScorerService().calculate_source_reputation("example.test", record) == expected


@pytest.mark.parametrize("first,second,expected", [
    ("Council approves library funding", "Council approves library funding today", True),
    ("Council approves", "Council approves", False),
    ("Council approves library funding", "Football team wins league trophy", False),
    ("", "Council approves library funding", False),
])
def test_related_report_requires_substantial_headline_overlap(first, second, expected):
    assert related_title(first, second) is expected


async def test_evidence_selection_and_score_are_order_independent():
    article = full_article()
    candidates = [{**article, "url": "https://other.test/z", "source": "Other"},
                  {**article, "url": "https://other.test/a", "source": "Other"},
                  {**article, "url": "https://third.test/report", "source": "Third"}]
    scorer = TrustScorerService()
    first = await scorer.calculate_trust_score(article, candidates)
    reversed_result = await scorer.calculate_trust_score(article, list(reversed(candidates)))
    assert first["trust_evidence"] == reversed_result["trust_evidence"]
    assert first["trust_score"] == reversed_result["trust_score"]
    assert [item["url"] for item in first["trust_evidence"]] == ["https://other.test/a", "https://third.test/report"]


async def test_worker_saves_long_article_summary_and_bounded_excerpt(monkeypatch):
    worker = NewsWorker()
    monkeypatch.setattr("app.worker.is_english_article", lambda *args: True)
    lead = "The city library opens on Monday. It contains a public archive. Residents can borrow books. The council published opening hours."
    body = lead + " " + "The archive contains books and newspapers for public access. " * 600
    raw = {**full_article(), "published_at": "2026-11-12T00:00:00Z", "content": body}
    assert await worker.process_article(raw)
    saved = await storage_service.get_article_by_url(raw["url"])
    assert saved.summary == lead
    assert saved.content_excerpt == body[:500]
    assert saved.processing_status == "completed"
    assert saved.published_date == datetime(2026, 11, 12)


async def test_empty_collection_completes_without_processing_articles(monkeypatch):
    worker = NewsWorker()
    monkeypatch.setattr(worker.news_fetcher, "fetch_all_sources", Mock(return_value=[]))
    result = await worker.fetch_and_process_news()
    assert {key: result[key] for key in ("fetched", "unique", "saved", "rescored")} == {
        "fetched": 0, "unique": 0, "saved": 0, "rescored": 0}
    assert "error" not in result
    assert result["finished_at"] >= result["started_at"]
    assert await storage_service.count_articles() == 0
