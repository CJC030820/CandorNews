"""Malay Mail and The Sun as trusted platforms."""
from unittest.mock import Mock
import app.main as main
from app.services import news_fetcher as nf
from app.services.news_fetcher import NewsFetcherService
from app.services.storage import storage_service
from app.services.trust_scorer import publisher_domain

FEED = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>Malay Mail  -  Malaysia</title>
<item><title>Police arrest four teenagers</title><link>https://www.malaymail.com/news/malaysia/2026/11/21/a</link>
<description>KUALA LUMPUR: Police said four teenagers were arrested.</description>
<pubDate>Sat, 21 Nov 2026 18:33:00 +0800</pubDate></item></channel></rss>"""


def test_platform_ids_and_publisher_domains():
    assert main.PLATFORMS["malaymail"] == "Malay Mail" and main.PLATFORMS["thesun"] == "The Sun"
    assert publisher_domain("https://www.malaymail.com/news/x") == "malaymail.com"
    assert publisher_domain("https://thesun.my/news/x") == "thesun.my"


def test_feed_gets_a_clean_publisher_name_and_fresh_copy(monkeypatch):
    get = Mock(return_value=Mock(content=FEED, raise_for_status=Mock()))
    monkeypatch.setattr(nf.requests, "get", get)
    articles = NewsFetcherService().fetch_from_rss("https://www.malaymail.com/feed/rss/malaysia", known_urls=set())
    assert articles[0]["source"] == "Malay Mail"
    assert "t" in get.call_args_list[0].kwargs["params"]  # the feed request asks past the publisher's cache


def test_refresh_for_selected_platforms_picks_their_feeds(monkeypatch):
    monkeypatch.setattr(nf.settings, "RSS_FEEDS", "https://www.nst.com.my/feed,https://www.malaymail.com/feed/rss/malaysia,"
                                                  "https://thesun.my/news/feed/")
    fetched = []
    fetcher = NewsFetcherService()
    monkeypatch.setattr(fetcher, "fetch_from_rss", lambda url, known=None: fetched.append(url) or [])
    fetcher.fetch_all_sources(["Malay Mail", "The Sun"])
    assert sorted(fetched) == ["https://thesun.my/news/feed/", "https://www.malaymail.com/feed/rss/malaysia"]


async def test_reputations_are_added_without_changing_stored_scores():
    await storage_service.source_credibility.insert_one(
        {"source_name": "Bernama", "domain": "bernama.com", "credibility_score": 50})
    await storage_service.seed_source_credibility()
    assert (await storage_service.get_source_credibility_by_domain("bernama.com")).credibility_score == 50
    assert (await storage_service.get_source_credibility_by_domain("malaymail.com")).credibility_score == 82
    assert (await storage_service.get_source_credibility_by_domain("thesun.my")).credibility_score == 78
    await storage_service.seed_source_credibility()  # running again adds nothing twice
    assert await storage_service.source_credibility.count_documents({"domain": "thesun.my"}) == 1


async def test_accounts_following_everything_get_the_new_platforms_once():
    users = storage_service.users
    await users.insert_many([
        {"email": "all@example.com", "followed_platforms": ["bernama", "nst", "fmt"]},
        {"email": "some@example.com", "followed_platforms": ["bernama"]},
        {"email": "unset@example.com"}])
    args = ("follow-test", ["bernama", "nst", "fmt"], ["malaymail", "thesun"])
    assert await storage_service.follow_new_platforms_once(*args) == 1
    assert (await users.find_one({"email": "all@example.com"}))["followed_platforms"] == [
        "bernama", "nst", "fmt", "malaymail", "thesun"]
    assert (await users.find_one({"email": "some@example.com"}))["followed_platforms"] == ["bernama"]
    # Someone who later unfollows the new ones is not changed again on the next restart.
    await users.update_one({"email": "all@example.com"}, {"$set": {"followed_platforms": ["bernama", "nst", "fmt"]}})
    assert await storage_service.follow_new_platforms_once(*args) == 0
    assert (await users.find_one({"email": "all@example.com"}))["followed_platforms"] == ["bernama", "nst", "fmt"]
