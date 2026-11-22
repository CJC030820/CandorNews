"""Developing stories: a story's updates over time (app/services/story_threads.py)."""
from datetime import datetime, timedelta
from types import SimpleNamespace

from app.models.article import ArticleCreate
from app.services import story_grouper, story_threads
from app.services.storage import storage_service

T0 = datetime(2026, 11, 18, 12, 0)


def make(url, title, hours, description, keywords=None):
    return ArticleCreate(title=title, url=url, source=url.split("/")[2], published_date=T0 + timedelta(hours=hours),
                         description=description, topic="General", topics=["General"], sentiment="Neutral",
                         trust_score=70.0, keywords=keywords or ["student", "school"], processing_status="completed")


def filler(n):
    """Unrelated articles, so the story's names and words count as rare."""
    return [make(f"https://www.thesun.my/f{i}", f"Unrelated headline number {i} about markets", -40 - i,
                 f"Traders in Singapore watched the Federal Reserve closely on day {i}.", ["markets"]) for i in range(n)]


DEATH = [
    ("https://www.nst.com.my/a", "Form Three student found dead at Kuala Kangsar boarding school", 0,
     "The Form Three student was found dead at the Kuala Kangsar boarding school, Perak Education Department said."),
    ("https://www.nst.com.my/b", "Kuala Kangsar boarding school death: Anwar orders immediate probe", 3,
     "Prime Minister Anwar Ibrahim ordered a probe into the Form Three death at Kuala Kangsar boarding school."),
    ("https://www.bernama.com/c", "Kuala Kangsar boarding school student died of neck compression, police say", 20,
     "Police said the Form Three student at the Kuala Kangsar boarding school died of neck compression."),
]


async def save_all(items):
    saved = []
    for item in items:
        created = await storage_service.create_article(item)
        await story_grouper.assign_story(created)
        saved.append(created)
    return saved


async def test_updates_of_a_developing_story_share_a_timeline():
    await save_all(filler(60))
    saved = await save_all([make(u, t, h, d) for u, t, h, d in DEATH])
    unrelated, = await save_all([make("https://www.freemalaysiatoday.com/z", "Penang ferry service resumes after repairs",
                                      5, "The Penang Port Commission said the ferry service resumed.", ["ferry"])])
    assert await story_threads.backfill_once() > 0
    threads = {(await storage_service.get_article_by_id(a.id)).thread_id for a in saved}
    assert len(threads) == 1
    assert (await storage_service.get_article_by_id(unrelated.id)).thread_id not in threads


async def test_versions_of_one_story_stay_in_one_thread():
    saved = await save_all(filler(40) + [
        make("https://www.nst.com.my/a", "Malaysia respects ICJ judgment in Myanmar genocide case", 0, "Wisma Putra said."),
        make("https://www.bernama.com/b", "World : Malaysia Respects ICJ Judgment In Myanmar Genocide Case", 1, "Wisma Putra said.")])
    await story_threads.backfill_once()
    a, b = [await storage_service.get_article_by_id(x.id) for x in saved[-2:]]
    assert a.story_id == b.story_id and a.thread_id == b.thread_id


def test_common_names_and_same_moment_pieces_are_not_updates():
    article = lambda i, title, hours, text, url: SimpleNamespace(
        id=i, title=title, url=url, published_date=T0 + timedelta(hours=hours), description=text, content_excerpt="")
    bnm = [article("1", "BNM sets out framework for open finance", 0,
                   "Bank Negara Malaysia Governor Abdul Rasheed Ghaffour said the framework is ready.", "https://www.bernama.com/1"),
           article("2", "Ringgit stable in near term, says BNM governor", 0.2,
                   "Bank Negara Malaysia Governor Abdul Rasheed Ghaffour said the ringgit is stable.", "https://www.bernama.com/2")]
    others = [article(f"o{i}", f"Unrelated headline {i}", -30, "Traders in Singapore watched markets.", "https://x.test/o")
              for i in range(40)]
    index = story_threads.ThreadIndex(bnm + others)
    assert not index.is_update(bnm[0], bnm[1])          # same outlet, same moment, different topics


async def test_article_page_timeline_lists_updates_oldest_first():
    import app.main as main
    await save_all(filler(60))
    saved = await save_all([make(u, t, h, d) for u, t, h, d in DEATH])
    await story_threads.backfill_once()
    current = await storage_service.get_article_by_id(saved[1].id)
    timeline = await main._story_timeline(current)
    assert [entry["title"][:20] for entry in timeline] == [t[:20] for _, t, _, _ in DEATH]
    assert [entry["current"] for entry in timeline] == [False, True, False]
    assert timeline[2]["sources"] == ["www.bernama.com"]   # the test articles use the host as publisher name


def test_digest_counts_a_developing_story_once_and_shows_its_latest_update():
    v = lambda i, story, thread, hours, trust: SimpleNamespace(id=i, story_id=story, thread_id=thread, source=f"S{i}",
                                                              trust_score=trust, published_date=T0 + timedelta(hours=hours))
    combined = story_grouper.combine_by_story([v("1", "a", "t", 0, 90), v("2", "b", "t", 5, 60), v("3", "b", "t", 6, 70),
                                               v("4", "c", None, 1, 50)])
    assert [c["article"].id for c in combined] == ["3", "4"]
    assert combined[0]["updates"] == 2 and combined[0]["also_reported_by"] == ["S2"]
