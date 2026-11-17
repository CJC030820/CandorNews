"""MongoDB storage contracts under mongomock; not real-server concurrency tests."""
from datetime import datetime, timedelta

import pytest
from pymongo.errors import DuplicateKeyError

from app.models.article import ArticleCreate
from app.models.user import UserCreate
from app.services.storage import storage_service


def article(**updates):
    values = dict(
        title="Transport committee publishes meeting minutes", source="Example News",
        url="https://example.com/minutes", author=None, published_date=datetime.utcnow(),
        description="The committee met on Tuesday.", summary="The committee met on Tuesday.",
        topic="Politics", topics=["Politics", "Technology"], keywords=["transport", "committee"],
        sentiment="Neutral", sentiment_score=0.0, trust_score=35.0,
        processing_status="completed",
    )
    values.update(updates)
    return ArticleCreate(**values)


async def test_article_round_trip_preserves_analysis_and_optional_fields():
    record = article()
    saved = await storage_service.create_article(record)
    by_id = await storage_service.get_article_by_id(saved.id)
    by_url = await storage_service.get_article_by_url(record.url)
    for actual in (by_id, by_url):
        assert actual.id == saved.id
        for field in ("title", "source", "url", "author", "description", "summary", "topic",
                      "topics", "keywords", "sentiment", "sentiment_score", "trust_score", "processing_status"):
            assert getattr(actual, field) == getattr(record, field)
        # BSON datetime precision is milliseconds.
        assert abs((actual.published_date - record.published_date).total_seconds()) < .001


async def test_unique_url_index_keeps_first_record_and_other_publisher():
    await storage_service.ensure_indexes()
    first = await storage_service.create_article(article())
    duplicate = await storage_service.create_article(article(title="Changed duplicate"))
    other = await storage_service.create_article(article(url="https://other.example/report", source="Other News"))
    assert duplicate is None
    assert first.id != other.id
    assert await storage_service.count_articles() == 2
    assert (await storage_service.get_article_by_id(first.id)).title == "Transport committee publishes meeting minutes"


async def test_unique_email_index_rejects_storage_duplicate():
    await storage_service.ensure_indexes()
    user = UserCreate(name="Reader", email="duplicate@example.com", password="Test-password-123")
    await storage_service.create_user(user)
    with pytest.raises(DuplicateKeyError):
        await storage_service.create_user(user)
    assert await storage_service.users.count_documents({}) == 1


async def test_index_initialization_is_idempotent():
    await storage_service.ensure_indexes()
    await storage_service.ensure_indexes()
    assert (await storage_service.articles.index_information())["url_1"]["unique"]
    assert (await storage_service.users.index_information())["email_1"]["unique"]


async def test_keyword_candidates_exclude_self_old_pending_and_unrelated():
    now = datetime.utcnow()
    await storage_service.create_article(article(published_date=now))
    relevant = await storage_service.create_article(article(url="https://other.example/new", published_date=now))
    await storage_service.create_article(article(url="https://other.example/old", published_date=now - timedelta(hours=80)))
    await storage_service.create_article(article(url="https://other.example/pending", processing_status="pending"))
    await storage_service.create_article(article(url="https://other.example/sports", keywords=["football"]))
    found = await storage_service.find_articles_by_keywords(["transport"], "https://example.com/minutes")
    assert [item.id for item in found] == [relevant.id]
    assert await storage_service.find_articles_by_keywords([], "https://example.com/minutes") == []


async def test_status_transition_controls_feed_visibility():
    saved = await storage_service.create_article(article(processing_status="pending"))
    assert await storage_service.get_latest_articles() == []
    timestamp = datetime(2026, 11, 1, 12)
    await storage_service.update_article_status(saved.id, "completed", timestamp)
    updated = await storage_service.get_article_by_id(saved.id)
    assert updated.processing_status == "completed"
    assert updated.processed_at == timestamp
    assert [item.id for item in await storage_service.get_latest_articles()] == [saved.id]


async def test_analysis_update_preserves_article_identity():
    saved = await storage_service.create_article(article())
    await storage_service.update_article_fields(saved.id, {"trust_score": 60.0, "trust_version": "test-version"})
    updated = await storage_service.get_article_by_id(saved.id)
    assert updated.trust_score == 60.0
    assert updated.trust_version == "test-version"
    assert updated.url == saved.url and updated.title == saved.title
    assert await storage_service.count_articles() == 1


@pytest.mark.parametrize("invalid_id", ["", "not-an-objectid", "a" * 23, "z" * 24])
async def test_invalid_article_id_is_safe(invalid_id):
    assert await storage_service.get_article_by_id(invalid_id) is None
