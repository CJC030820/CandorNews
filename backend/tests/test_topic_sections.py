"""Topic tagging: the publisher's section and weak keywords (app/services/topic_classifier.py)."""
from datetime import datetime

import pytest

from app.models.article import ArticleCreate
from app.services.storage import storage_service
from app.services.topic_classifier import TopicClassifierService
from app.worker import NewsWorker

tc = TopicClassifierService()

POWER = dict(
    title="Four Kelana Jaya Line stations affected by power disruption",
    description="KUALA LUMPUR: Four stations on the Kelana Jaya LRT line were affected by a power disruption this "
                "morning, Rapid KL said.",
    content="A team of technicians was sent to restore power. Police were at the stations to help commuters. "
            "Services from Putrajaya were not affected.",
    url="https://www.nst.com.my/news/nation/2026/11/1585950/four-kelana-jaya-line-stations-affected-power-disruption")


def test_one_weak_word_in_the_body_does_not_add_a_topic():
    topics = tc.classify_topics(**POWER)
    assert topics == ["Local Malaysia News"]          # not Sports ("team") or Crime ("police")


def test_two_weak_words_or_a_weak_word_in_the_headline_still_count():
    assert "Crime" in tc.classify_topics("Man held", "Police detained a suspect after the robbery attempt.")
    assert "Sports" in tc.classify_topics("Harimau Malaya team named for qualifier")


@pytest.mark.parametrize("url,title,expected", [
    ("https://www.nst.com.my/sports/football/2026/11/1/x", "De Bruyne still loves City owners", "Sports"),
    ("https://www.freemalaysiatoday.com/category/sports/2026/11/24/x", "Senegal reinstated as winners", "Sports"),
    ("https://www.bernama.com/en/news.php?id=1", "Sport : Sivasangari Storms Into Semi-Finals", "Sports"),
    ("https://www.freemalaysiatoday.com/category/business/2026/11/24/x", "Firm posts record quarter", "Business"),
    ("https://www.nst.com.my/news/nation/2026/11/1/x", "Ferry service resumes", "Local Malaysia News"),
    ("https://www.nst.com.my/lifestyle/2026/11/1/x", "#SHOWBIZ: Andy Lau surprises fans", "Entertainment"),
])
def test_publisher_section_comes_first(url, title, expected):
    assert tc.classify_topics(title, url=url)[0] == expected


def test_sports_words_in_a_news_section_need_strong_evidence():
    url = "https://www.nst.com.my/news/nation/2026/11/1/x"
    assert "Sports" not in tc.classify_topics("Final report on LRT disruption", "The team found a faulty cable.", url=url)
    assert "Sports" in tc.classify_topics("Johor allocates RM217mil for youth and sports",
                                          "The football league and athlete programmes get more money.", url=url)


async def test_stored_articles_are_retagged_once():
    stored = await storage_service.create_article(ArticleCreate(
        title=POWER["title"], url=POWER["url"], source="New Straits Times", published_date=datetime(2026, 11, 26),
        description=POWER["description"], content_excerpt=POWER["content"], topic="Local Malaysia News",
        topics=["Local Malaysia News", "Crime", "Sports"], sentiment="Neutral", trust_score=70.0,
        processing_status="completed"))
    worker = NewsWorker()
    assert await worker.retag_topics_once() == 1
    fresh = await storage_service.get_article_by_id(stored.id)
    assert fresh.topics == ["Local Malaysia News"] and fresh.topic == "Local Malaysia News"
    assert await worker.retag_topics_once() == 0      # only once
