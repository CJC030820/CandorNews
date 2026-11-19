"""Bookmarks and history are saved to the account, so a PC and a phone
signed in with the same email see the same records."""
import pytest
from httpx import ASGITransport, AsyncClient

from app import main
from app.core.security import create_access_token
from app.models.user import UserCreate
from app.services.storage import storage_service


@pytest.fixture
async def api():
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as client:
        yield client


async def headers_for(email):
    await storage_service.create_user(UserCreate(name="Reader", email=email, password="Test-password-123"))
    return {"Authorization": f"Bearer {create_access_token({'sub': email})}"}


def article(i, **extra):
    return {"id": str(i), "title": f"Story {i}", "source": "Example News", "categories": ["Politics"], **extra}


async def test_bookmark_saved_on_one_device_appears_on_another(api):
    pc = await headers_for("same@example.com")
    phone = {"Authorization": f"Bearer {create_access_token({'sub': 'same@example.com'})}"}
    assert (await api.put("/api/me/bookmarks/1", json={"article": article(1)}, headers=pc)).status_code == 200
    assert (await api.put("/api/me/history/2", json={"article": article(2)}, headers=pc)).status_code == 200

    lib = (await api.get("/api/me/library", headers=phone)).json()
    assert [b["id"] for b in lib["bookmarks"]] == ["1"]
    assert lib["bookmarks"][0]["title"] == "Story 1" and lib["bookmarks"][0]["savedAt"].endswith("Z")
    assert [h["id"] for h in lib["history"]] == ["2"]

    await api.delete("/api/me/bookmarks/1", headers=phone)
    await api.delete("/api/me/history", headers=phone)
    lib = (await api.get("/api/me/library", headers=pc)).json()
    assert lib == {"bookmarks": [], "history": []}


async def test_accounts_do_not_see_each_other(api):
    a = await headers_for("a@example.com")
    b = await headers_for("b@example.com")
    await api.put("/api/me/bookmarks/1", json={"article": article(1)}, headers=a)
    assert (await api.get("/api/me/library", headers=b)).json()["bookmarks"] == []


async def test_import_merges_device_records_without_duplicates(api):
    h = await headers_for("merge@example.com")
    pc = {"bookmarks": [article(1, savedAt="2026-11-10T08:00:00.000Z")],
          "history": [article(1, readAt="2026-11-10T08:00:00.000Z"), article(2, readAt="2026-11-12T08:00:00.000Z")]}
    phone = {"bookmarks": [article(1, savedAt="2026-11-15T08:00:00.000Z"), article(3, savedAt="2026-11-16T08:00:00.000Z")],
             "history": [article(1, readAt="2026-11-18T08:00:00.000Z")]}
    await api.post("/api/me/library/import", json=pc, headers=h)
    lib = (await api.post("/api/me/library/import", json=phone, headers=h)).json()

    assert [b["id"] for b in lib["bookmarks"]] == ["3", "1"]
    assert lib["bookmarks"][1]["savedAt"] == "2026-11-10T08:00:00.000Z"  # first save kept
    assert [x["id"] for x in lib["history"]] == ["1", "2"]                # latest view on top
    assert lib["history"][0]["readAt"] == "2026-11-18T08:00:00.000Z"


async def test_reading_again_moves_story_to_top(api):
    h = await headers_for("again@example.com")
    for i in (1, 2, 1):
        await api.put(f"/api/me/history/{i}", json={"article": article(i)}, headers=h)
    assert [x["id"] for x in (await api.get("/api/me/library", headers=h)).json()["history"]] == ["1", "2"]


async def test_snapshot_drops_unknown_fields_and_limits_size(api):
    h = await headers_for("snap@example.com")
    await api.put("/api/me/bookmarks/1", headers=h,
                  json={"article": article(1, title="x" * 5000, secret="nope", trustScore=81.234)})
    saved = (await api.get("/api/me/library", headers=h)).json()["bookmarks"][0]
    assert "secret" not in saved and len(saved["title"]) == 500 and saved["trustScore"] == 81.23


async def test_library_requires_login_and_valid_id(api):
    assert (await api.get("/api/me/library")).status_code == 401
    h = await headers_for("id@example.com")
    assert (await api.put("/api/me/bookmarks/" + "x" * 65, json={"article": {}}, headers=h)).status_code == 400


async def test_deleting_account_removes_library(api):
    h = await headers_for("gone@example.com")
    await api.put("/api/me/bookmarks/1", json={"article": article(1)}, headers=h)
    await api.request("DELETE", "/api/users/me", headers=h, json={"password": "Test-password-123"})
    assert await storage_service.user_library.count_documents({}) == 0
