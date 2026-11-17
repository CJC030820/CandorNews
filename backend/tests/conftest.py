import pytest
from mongomock_motor import AsyncMongoMockClient
from app.services.storage import storage_service


@pytest.fixture(autouse=True)
def isolated_database(monkeypatch):
    """Exercise actual storage methods without touching the user's MongoDB."""
    client = AsyncMongoMockClient()
    db = client.fyp_tests
    for name, value in {"client": client, "db": db, "users": db.users,
                        "articles": db.articles, "interactions": db.interactions,
                        "source_credibility": db.source_credibility}.items():
        monkeypatch.setattr(storage_service, name, value)
    return storage_service
