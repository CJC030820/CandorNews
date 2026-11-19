"""Bookmarks and reading history stored per account, so every device that
signs in with the same email sees the same records.

One document per (user, kind, article): kind is "bookmark" or "history".
Only a small, size-limited copy of the article is kept for display.
"""
from datetime import datetime, timezone
from typing import Iterable, Optional

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from app.services.storage import storage_service

KINDS = {"bookmark", "history"}
MAX_ITEMS = {"bookmark": 500, "history": 300}
TEXT_FIELDS = {"id": 64, "title": 500, "source": 200, "description": 1500, "image": 1000, "url": 1000,
               "category": 60, "trustLabel": 60, "sentiment": 30, "toneLabel": 60, "rawDate": 40,
               "author": 200}


async def _upsert(query: dict, update: dict):
    """Two devices saving the same story at once: the loser retries as an update."""
    try:
        await _col().update_one(query, update, upsert=True)
    except DuplicateKeyError:
        await _col().update_one(query, update)


def _col():
    return storage_service.user_library


async def ensure_indexes():
    await _col().create_index([("user_id", ASCENDING), ("kind", ASCENDING), ("article_id", ASCENDING)], unique=True)
    await _col().create_index([("user_id", ASCENDING), ("kind", ASCENDING), ("at", DESCENDING)])


def valid_article_id(value) -> Optional[str]:
    text = str(value or "").strip()
    return text if 0 < len(text) <= 64 else None


def snapshot(article: dict) -> dict:
    """Keep only display fields, with length limits."""
    article = article if isinstance(article, dict) else {}
    out = {}
    for key, limit in TEXT_FIELDS.items():
        value = article.get(key)
        if isinstance(value, (str, int, float)) and not isinstance(value, bool):
            out[key] = str(value)[:limit]
    categories = article.get("categories")
    if isinstance(categories, list):
        out["categories"] = [str(c)[:60] for c in categories if isinstance(c, str)][:5]
    score = article.get("trustScore")
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        out["trustScore"] = round(float(score), 2)
    if article.get("imageStored") is True:
        out["imageStored"] = True
    return out


def _parse_time(value) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _iso(value: datetime) -> str:
    return value.replace(tzinfo=None).isoformat(timespec="milliseconds") + "Z"


async def list_items(user_id: str, kind: str) -> list:
    cursor = _col().find({"user_id": user_id, "kind": kind}).sort("at", DESCENDING).limit(MAX_ITEMS[kind])
    field = "savedAt" if kind == "bookmark" else "readAt"
    items = []
    async for doc in cursor:
        items.append({**doc.get("article", {}), "id": doc["article_id"], field: _iso(doc["at"])})
    return items


async def _trim(user_id: str, kind: str):
    """Keep only the newest MAX_ITEMS entries."""
    extra = _col().find({"user_id": user_id, "kind": kind}, {"_id": 1}).sort("at", DESCENDING).skip(MAX_ITEMS[kind])
    ids = [doc["_id"] async for doc in extra]
    if ids:
        await _col().delete_many({"_id": {"$in": ids}})


async def save(user_id: str, kind: str, article_id: str, article: dict, at: Optional[datetime] = None):
    """Bookmark: keeps the first save time. History: moves to the top with the new time."""
    now = at or datetime.utcnow()
    data = snapshot(article)
    data["id"] = article_id
    if kind == "bookmark":
        update = {"$setOnInsert": {"at": now}, "$set": {"article": data}}
    else:
        update = {"$set": {"at": now, "article": data}}
    await _upsert({"user_id": user_id, "kind": kind, "article_id": article_id}, update)
    await _trim(user_id, kind)


async def remove(user_id: str, kind: str, article_id: str) -> int:
    result = await _col().delete_one({"user_id": user_id, "kind": kind, "article_id": article_id})
    return result.deleted_count


async def clear(user_id: str, kind: str) -> int:
    result = await _col().delete_many({"user_id": user_id, "kind": kind})
    return result.deleted_count


async def merge(user_id: str, kind: str, items: Iterable[dict]) -> int:
    """Add records kept on a device. Bookmarks keep the earliest save time,
    history keeps the latest view time; existing server copies win."""
    field = "savedAt" if kind == "bookmark" else "readAt"
    added = 0
    for item in list(items or [])[: MAX_ITEMS[kind]]:
        if not isinstance(item, dict):
            continue
        article_id = valid_article_id(item.get("id"))
        when = _parse_time(item.get(field))
        if not article_id or not when:
            continue
        data = snapshot(item)
        data["id"] = article_id
        op = "$min" if kind == "bookmark" else "$max"
        await _upsert({"user_id": user_id, "kind": kind, "article_id": article_id},
                      {op: {"at": when}, "$setOnInsert": {"article": data}})
        added += 1
    await _trim(user_id, kind)
    return added


async def delete_user(user_id: str) -> int:
    result = await _col().delete_many({"user_id": user_id})
    return result.deleted_count
