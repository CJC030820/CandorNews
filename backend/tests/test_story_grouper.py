"""One story reported by several publishers (app/services/story_grouper.py)."""
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.models.article import ArticleCreate
from app.services import story_grouper
from app.services.storage import storage_service
from app.services.trust_scorer import related_title

T0 = datetime(2026, 11, 20, 9, 0)


def article(url, title, hours=0, description="", source=None, trust=70.0, keywords=None):
    return ArticleCreate(
        title=title, url=url, source=source or url.split("/")[2], published_date=T0 + timedelta(hours=hours),
        description=description, topic="General", topics=["General"], sentiment="Neutral",
        trust_score=trust, keywords=keywords or ["icj", "myanmar", "judgment", "malaysia"],
        processing_status="completed")


async def save(*items):
    saved = []
    for item in items:
        created = await storage_service.create_article(item)
        await story_grouper.assign_story(created)
        saved.append(created)
    return [await storage_service.get_article_by_id(a.id) for a in saved]


@pytest.mark.parametrize("first,second,same", [
    ("Sport : Sivasangari Storms Into China Open Semi-Finals", "Sivasangari storms into China Open semi-finals", True),
    ("Armizan: GRS to decide GE16 direction collectively", "GRS's direction for GE16 will be decided collectively, says Armizan", True),
    ("Sivasangari storms into China Open semi-finals", "Sivasangari surges into China Open final", False),
    ("Wei Chong-Kai Wun storm into Hong Kong Open last eight", "Wei Chong-Kai Wun cruise into Hong Kong Open semis", False),
    ("Council approves", "Council approves", False),
])
def test_same_story_headlines(first, second, same):
    assert related_title(first, second) is same


async def test_versions_from_different_publishers_share_a_story():
    a, b, c = await save(
        article("https://www.bernama.com/a", "World : Malaysia Respects ICJ Judgment In Myanmar Genocide Case"),
        article("https://www.nst.com.my/b", "Malaysia respects ICJ judgment in Myanmar genocide case", hours=1),
        article("https://www.freemalaysiatoday.com/c", "Malaysia respects ICJ judgment on Rohingya genocide in Myanmar", hours=2))
    assert a.story_id == b.story_id == c.story_id


async def test_different_story_or_too_far_apart_stays_separate():
    a, b, c = await save(
        article("https://www.bernama.com/a", "Malaysia respects ICJ judgment in Myanmar genocide case"),
        article("https://www.nst.com.my/b", "Football team wins league trophy", hours=1),
        article("https://www.freemalaysiatoday.com/c", "Malaysia respects ICJ judgment in Myanmar genocide case", hours=60))
    assert len({a.story_id, b.story_id, c.story_id}) == 3


async def test_two_different_stories_from_one_publisher_do_not_join():
    a, b = await save(
        article("https://www.nst.com.my/a", "Putin slams sanctions ahead of summit with Trump, Xi"),
        article("https://www.freemalaysiatoday.com/b", "Putin slams Western sanctions ahead of summit with Trump, Xi", hours=1))
    c, = await save(article("https://www.nst.com.my/c", "Xi welcomes Trump to Beijing for summit talks", hours=2))
    assert a.story_id == b.story_id != c.story_id


async def test_backfill_groups_stored_articles_once():
    for item in (article("https://www.bernama.com/a", "Malaysia respects ICJ judgment in Myanmar genocide case"),
                 article("https://www.nst.com.my/b", "Malaysia respects ICJ judgment in Myanmar genocide case", hours=1)):
        await storage_service.create_article(item)
    assert await story_grouper.backfill_once() == 2
    stories = {a.story_id for a in await storage_service.get_all_articles_oldest_first()}
    assert len(stories) == 1 and None not in stories
    assert await story_grouper.backfill_once() == 0          # only once


def test_combine_by_story_keeps_best_scored_version_and_names_others():
    v = lambda i, story, source, trust, hours: SimpleNamespace(id=i, story_id=story, source=source, trust_score=trust,
                                                              published_date=T0 + timedelta(hours=hours))
    combined = story_grouper.combine_by_story([v("1", "s", "NST", 70, 1), v("2", "s", "Bernama", 82, 0),
                                               v("3", None, "FMT", 60, 0), v("4", "s", "FMT", 75, 2)])
    assert [c["article"].id for c in combined] == ["2", "3"]
    assert combined[0]["also_reported_by"] == ["NST", "FMT"]


def test_distinctive_details_show_what_only_one_version_mentions():
    details = story_grouper.distinctive_details({
        "fmt": ("AG opposed house arrest", "The minutes show Attorney-General Dusuki Mokhtar opposed it, "
                "and the RM50 million fine stands, the board said."),
        "nst": ("A-G objected to house arrest", "PUTRAJAYA: The board minutes show the A-G objected. "
                "\"We followed the law,\" a board member said on Monday."),
        "bernama": ("General : AG Objected To House Arrest", "From Nabilah Saleh KUALA LUMPUR, Nov 18 (Bernama) -- "
                    "The AG objected, minutes show, in 2 of the cases."),
    })
    assert "RM50 million" in details["fmt"] and "Attorney-General Dusuki Mokhtar" in details["fmt"]
    assert any(d.startswith("“We followed the law") for d in details["nst"])
    assert details["bernama"] == []            # byline, dateline and a bare small number are not details


async def test_article_page_lists_the_other_versions(monkeypatch):
    import app.main as main
    a, b = await save(
        article("https://www.bernama.com/a", "Malaysia respects ICJ judgment in Myanmar genocide case",
                description="Malaysia respects the ruling, the ministry said."),
        article("https://www.nst.com.my/b", "Malaysia respects ICJ judgment in Myanmar genocide case", hours=1,
                description="Wisma Putra said the 15 judges ruled on the case."))
    comparison = await main._story_comparison(a)
    assert [v["id"] for v in comparison["storyVersions"]] == [b.id]
    assert comparison["reportedFirst"] is True and comparison["storyVersions"][0]["first"] is False
    assert "Wisma Putra" in comparison["storyVersions"][0]["uniqueDetails"]
