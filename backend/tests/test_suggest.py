"""Search keyword suggestions."""
from datetime import datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app import main
from app.core.security import create_access_token
from app.models.user import UserCreate
from app.services.storage import storage_service
from app.services.suggest import build_suggestions, tokens, trending
from tests.test_api_contracts import article_data

TITLES = [
    "General : Malaysia Strengthens Cooperation To Address Climate Change At COP31",
    "Climate change to cut palm oil output, study finds",
    "Climate change: Sabah farmers adapt",
    "Clinic opens in Kuching",
    "Anwar holds talks with Chinese firms",
    "Anwar to visit Japan next week",
]
texts = lambda q: [s["text"] for s in build_suggestions(TITLES, q)]


def test_headline_prefix_is_removed():
    assert tokens("General : HSBC Opens Centre")[0] == "HSBC"


def test_completes_the_word_being_typed_and_offers_phrases():
    # "climate change" is in three headlines; capitals only where the news uses them
    assert texts("cli") == ["climate", "climate change", "clinic"]


def test_phrase_needs_two_headlines():
    assert "clinic opens" not in texts("cli")


def test_keeps_earlier_words_and_completes_the_last():
    assert texts("climate ch") == ["climate change"]


def test_after_a_space_suggests_the_next_word():
    assert texts("anwar ") == ["anwar holds"]        # "to" is a filler word, so "anwar to" is skipped
    assert texts("climate ") == ["climate change"]


def test_common_words_and_exact_query_are_not_suggested():
    assert texts("the") == []
    assert "anwar" not in [t.lower() for t in texts("anwar")]


def test_plural_and_singular_are_one_suggestion_and_acronyms_stay_upper():
    out = build_suggestions(["Floods hit Kelantan", "More floods in Pahang", "Flood relief arrives",
                             "COP31 talks open", "COP31 ends with deal", "Cop arrested"], "f")
    assert [s["text"] for s in out] == ["floods"] and out[0]["count"] == 3
    assert build_suggestions(["COP31 talks open", "COP31 ends with deal"], "cop")[0]["text"] == "COP31"


def test_trending_uses_headlines_prefers_phrases_and_skips_fillers():
    titles = ["Climate change talks in Kuala Lumpur", "Climate change hits farmers", "New climate change fund",
              "Sabah farmers welcome visit by Anwar", "Japan hosts talks with Anwar", "RM5 million per cent rise"]
    out = trending(titles)
    shown = [s["text"] for s in out]
    assert shown[0] == "climate change" and out[0]["count"] == 3
    assert "Anwar" in shown                                   # a name keeps its capital
    assert not {"climate", "change", "kuala", "lumpur", "million", "per", "cent"} & set(shown)


@pytest.fixture
async def api():
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as client:
        yield client


async def test_suggest_endpoint(api):
    await storage_service.create_user(UserCreate(name="R", email="s@example.com", password="Test-password-123"))
    h = {"Authorization": f"Bearer {create_access_token({'sub': 's@example.com'})}"}
    now = datetime.utcnow()
    for i, t in enumerate(TITLES):
        await storage_service.create_article(article_data(title=t, url=f"https://example.com/{i}",
                                                          published_date=now - timedelta(hours=i),
                                                          keywords=["climate", "change"] if "limate" in t else ["anwar"]))
    data = (await api.get("/api/articles/suggest", params={"q": "clim"}, headers=h)).json()
    assert data["kind"] == "completions" and data["suggestions"][0]["text"].lower().startswith("climate")
    data = (await api.get("/api/articles/suggest", params={"q": ""}, headers=h)).json()
    assert data["kind"] == "trending"
    assert data["suggestions"][0]["text"] == "climate change"
    assert (await api.get("/api/articles/suggest", params={"q": "x" * 61}, headers=h)).status_code == 422
    assert (await api.get("/api/articles/suggest", params={"q": "clim"})).status_code == 401
    # regex characters are treated literally
    assert (await api.get("/api/articles/suggest", params={"q": ".*"}, headers=h)).json()["suggestions"] == []
