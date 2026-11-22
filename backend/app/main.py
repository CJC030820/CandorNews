from fastapi import FastAPI, HTTPException, Depends, Query, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncio
import hashlib
import json
import time
from fastapi.encoders import jsonable_encoder
from uuid import uuid4
from pymongo.errors import DuplicateKeyError
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import os
import logging
import html
import re
from pydantic import BaseModel, EmailStr, Field, field_validator
from jose import JWTError, jwt
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


from fastapi.responses import FileResponse
from app.services import email_service, email_verification, image_cache, library, story_grouper, story_threads, suggest
from app.services.trust_scorer import SCORE_VERSION
from app.services.notification_times import LEGACY_PRESETS, MAX_TIMES, due_times, normalize_times, user_times
from app.services.storage import storage_service
from app.core.security import get_password_hash, verify_password, create_access_token, issued_before_account
from app.core.config import settings
from app.models.user import UserCreate as DBUserCreate
from app.worker import news_worker

logger = logging.getLogger(__name__)

VALID_EMAIL_SCHEDULES = {"morning", "night", "both"}

class RefreshRequest(BaseModel):
    platforms: List[str] = []


# JWT settings (kept in sync with app/core/security.py via settings)
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES



app = FastAPI(
    title="Trust-Aware Personalized AI News Intelligence System",
    description="API for the news intelligence system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    """Ensure database indexes exist so accounts persist reliably, start the
    scheduled email notification checks (custom times), and start the background
    news ingestion worker that fetches the latest headlines from configured RSS feeds (runs immediately, then every WORKER_INTERVAL_MINUTES)."""
    try:
        await storage_service.ensure_indexes()
        await library.ensure_indexes()
        print("MongoDB indexes ensured. User accounts will persist across restarts.")
    except Exception as exc:
        print(f"Warning: could not ensure MongoDB indexes: {exc}")

    try:
        await storage_service.seed_source_credibility()
        print("Source credibility scores seeded (used for trust score calculation).")
    except Exception as exc:
        print(f"Warning: could not seed source credibility: {exc}")

    try:
        added = await storage_service.follow_new_platforms_once(
            "follow-malaymail-thesun", ["bernama", "nst", "fmt"], ["malaymail", "thesun"])
        if added:
            print(f"Malay Mail and The Sun added for {added} account(s) that followed every publisher.")
    except Exception as exc:
        print(f"Warning: could not add new platforms to followed lists: {exc}")

    try:
        start_email_scheduler()
        print("Email notification scheduler started (checks custom delivery times every minute).")
    except Exception as exc:
        print(f"Warning: could not start email scheduler: {exc}")

    async def group_stored_articles():
        try:
            async with news_worker._fetch_lock:     # never at the same time as a collection run
                await story_grouper.backfill_once()
                await story_threads.backfill_once()
        except Exception as exc:
            logger.error(f"Could not group stored articles into stories: {exc}", exc_info=True)
    asyncio.create_task(group_stored_articles())

    try:
        news_worker.start()
        print("News ingestion worker started (fetching latest news in the background).")
    except Exception as exc:
        print(f"Warning: could not start news ingestion worker: {exc}")


@app.on_event("shutdown")
async def on_shutdown():
    for task in list(refresh_tasks):
        task.cancel()
    await asyncio.gather(*refresh_tasks, return_exceptions=True)
    try:
        email_scheduler.shutdown(wait=False)
    except Exception:
        pass
    try:
        news_worker.stop()
    except Exception:
        pass


# Pydantic models (API request/response contracts)
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def valid_name(cls, value):
        if not value.strip():
            raise ValueError("Name cannot be blank")
        return value.strip()

    @field_validator("password")
    @classmethod
    def valid_password(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes")
        return value

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    preferred_topics: list = []
    email_notifications_enabled: bool = False
    email_notification_schedule: str = "morning"
    email_notification_times: List[str] = ["07:00"]
    email_verified: bool = False
    followed_platforms: Optional[List[str]] = None

# Publishers users can follow: id -> name used in article sources.
PLATFORMS = {"bernama": "Bernama", "nst": "New Straits Times", "fmt": "Free Malaysia Today",
             "malaymail": "Malay Mail", "thesun": "The Sun"}


def _followed_names(user):
    """Names of the publishers a user follows (None = all publishers)."""
    ids = getattr(user, "followed_platforms", None) or []
    names = [PLATFORMS[i] for i in ids if i in PLATFORMS]
    return names or None


def from_followed(articles, platform_ids):
    """Keep articles from the followed publishers (all when none chosen)."""
    names = [PLATFORMS[i].lower() for i in (platform_ids or []) if i in PLATFORMS]
    if not names:
        return list(articles)
    return [a for a in articles if any(n in (a.source or "").lower() for n in names)]


class PlatformsUpdate(BaseModel):
    platform_ids: List[str] = Field(min_length=1, max_length=len(PLATFORMS))

    @field_validator("platform_ids")
    @classmethod
    def known_platforms(cls, values):
        if any(value not in PLATFORMS for value in values):
            raise ValueError("Unknown platform")
        return list(dict.fromkeys(values))

class PreferencesUpdate(BaseModel):
    preferred_topics: List[str] = Field(default_factory=list, max_length=11)

    @field_validator("preferred_topics")
    @classmethod
    def supported_topics(cls, values):
        allowed = {"Politics", "Business", "Health", "Sports", "Entertainment", "Technology", "AI", "Finance", "Crime", "Local Malaysia News", "General"}
        if any(value not in allowed for value in values):
            raise ValueError("Unsupported topic")
        return list(dict.fromkeys(values))

class UserProfileUpdate(BaseModel):
    name: str

class AccountDeleteRequest(BaseModel):
    password: str

class EmailSettingsUpdate(BaseModel):
    email_notifications_enabled: Optional[bool] = None
    # Legacy preset (morning/night/both); prefer email_notification_times.
    email_notification_schedule: Optional[str] = None
    # One to three "HH:MM" delivery times in EMAIL_TIMEZONE.
    email_notification_times: Optional[List[str]] = Field(default=None, max_length=10)

class EmailTestMessage(BaseModel):
    message: Optional[str] = Field(default=None, max_length=300)

class EmailVerificationConfirm(BaseModel):
    code: str = Field(min_length=1, max_length=12)


def _user_to_response(user) -> UserResponse:
    """Convert a UserInDB (MongoDB-backed) model into the API UserResponse."""
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        preferred_topics=user.preferred_topics or [],
        email_notifications_enabled=getattr(user, "email_notifications_enabled", False),
        email_notification_schedule=getattr(user, "email_notification_schedule", "morning") or "morning",
        email_notification_times=user_times(user),
        email_verified=bool(getattr(user, "email_verified", False)),
        followed_platforms=getattr(user, "followed_platforms", None),
    )


bearer = HTTPBearer(auto_error=False)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    token = credentials.credentials if credentials else None
    """Resolve the current user from a JWT token, always reading fresh from
    MongoDB so accounts and settings persist across server restarts."""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await storage_service.get_user_by_email(email)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if issued_before_account(payload, user.created_at):
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    return user

# Routes
@app.get("/")
async def root():
    return {"message": "Welcome to the Trust-Aware Personalized AI News Intelligence System API"}

@app.get("/health")
async def health_check():
    try:
        await storage_service.client.admin.command("ping")
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/api/auth/register", response_model=UserResponse)
async def register(user: UserCreate):
    """Register a new account. Stored permanently in MongoDB, so the account
    and password remain available even after the server/container restarts."""
    existing_user = await storage_service.get_user_by_email(user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    try:
        new_user = await storage_service.create_user(
            DBUserCreate(
                name=user.name,
                email=user.email,
                password=user.password,
                preferred_topics=[],
                email_notifications_enabled=False,
                email_notification_schedule="morning",
                email_notification_times=["07:00"]
            )
        )
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Email already registered")

    return _user_to_response(new_user)

@app.post("/api/auth/login", response_model=Token)
async def login(user: UserLogin):
    """Log in with a previously registered email/password. Works after any
    number of server restarts since credentials are persisted in MongoDB."""
    stored_user = await storage_service.get_user_by_email(user.email)
    if not stored_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(user.password, stored_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": stored_user.email},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(user=Depends(get_current_user)):
    return _user_to_response(user)

@app.put("/api/users/preferences")
async def update_preferences(preferences: PreferencesUpdate, user=Depends(get_current_user)):
    allowed_topics = preferences.preferred_topics
    updated_user = await storage_service.update_user_by_email(
        user.email,
        {"preferred_topics": allowed_topics}
    )

    return _user_to_response(updated_user)


@app.put("/api/users/platforms", response_model=UserResponse)
async def update_platforms(update: PlatformsUpdate, user=Depends(get_current_user)):
    """Save the followed publishers to the account (shared by all devices)."""
    updated_user = await storage_service.update_user_by_email(user.email, {"followed_platforms": update.platform_ids})
    return _user_to_response(updated_user)


@app.put("/api/users/profile", response_model=UserResponse)
async def update_profile(profile: UserProfileUpdate, user=Depends(get_current_user)):
    """Update the current user's display name. Persisted permanently in
    MongoDB, so the new name survives server restarts and future logins."""
    new_name = profile.name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Name cannot be empty.")

    updated_user = await storage_service.update_user_by_email(
        user.email,
        {"name": new_name}
    )

    return _user_to_response(updated_user)


@app.delete("/api/users/me")
async def delete_account(request: AccountDeleteRequest, user=Depends(get_current_user)):
    """Permanently delete the current user's account. Requires the account
    password to be re-entered as a safety confirmation. This action cannot
    be undone - the user document is removed from MongoDB entirely."""

    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect password.")

    deleted = await storage_service.delete_user_by_email(user.email)
    if deleted:
        await library.delete_user(user.id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete account. Please try again.")

    return {"status": "deleted", "detail": "Your account has been permanently deleted."}


# ---- Bookmarks and reading history, saved per account (shared by all devices) ----

class LibraryArticle(BaseModel):
    article: dict = Field(default_factory=dict)


class LibraryImport(BaseModel):
    bookmarks: List[dict] = Field(default_factory=list, max_length=500)
    history: List[dict] = Field(default_factory=list, max_length=300)


def _library_id(article_id: str) -> str:
    valid = library.valid_article_id(article_id)
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid article id.")
    return valid


async def _library(user) -> dict:
    return {"bookmarks": await library.list_items(user.id, "bookmark"),
            "history": await library.list_items(user.id, "history")}


@app.get("/api/me/library")
async def get_library(user=Depends(get_current_user)):
    return await _library(user)


@app.post("/api/me/library/import")
async def import_library(payload: LibraryImport, user=Depends(get_current_user)):
    """Merge records kept on a device into the account (no duplicates)."""
    await library.merge(user.id, "bookmark", payload.bookmarks)
    await library.merge(user.id, "history", payload.history)
    return await _library(user)


@app.put("/api/me/bookmarks/{article_id}")
async def save_bookmark(article_id: str, payload: LibraryArticle, user=Depends(get_current_user)):
    await library.save(user.id, "bookmark", _library_id(article_id), payload.article)
    return {"status": "saved"}


@app.delete("/api/me/bookmarks/{article_id}")
async def delete_bookmark(article_id: str, user=Depends(get_current_user)):
    await library.remove(user.id, "bookmark", _library_id(article_id))
    return {"status": "removed"}


@app.put("/api/me/history/{article_id}")
async def save_history(article_id: str, payload: LibraryArticle, user=Depends(get_current_user)):
    await library.save(user.id, "history", _library_id(article_id), payload.article)
    return {"status": "saved"}


@app.delete("/api/me/history/{article_id}")
async def delete_history_item(article_id: str, user=Depends(get_current_user)):
    await library.remove(user.id, "history", _library_id(article_id))
    return {"status": "removed"}


@app.delete("/api/me/history")
async def clear_history(user=Depends(get_current_user)):
    await library.clear(user.id, "history")
    return {"status": "cleared"}

def _repair_mojibake(value: str) -> str:
    """Repair common UTF-8-as-Windows-1252 corruption in stored text."""
    if not value or not re.search(r"[ÃÂâ€™â€œâ€â€“â€”â€¦ðŸ]", value):
        return value
    try:
        repaired = value.encode("cp1252").decode("utf-8")
        return repaired if repaired != value else value
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def _clean_display_text(value) -> str:
    """Normalize entities, mojibake, and non-breaking whitespace."""
    if not value:
        return ""
    text = html.unescape(str(value))
    text = _repair_mojibake(text)
    return re.sub(r"[\s\u00a0\u2007\u202f]+", " ", text).strip()

def _article_to_feed_dict(article, detail: bool = True) -> dict:
    """Convert a stored ArticleInDB into the shape the frontend expects."""
    published = article.published_date
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    date_str = published.isoformat() if hasattr(published, "isoformat") else str(published)
    categories = getattr(article, "topics", None) or ([article.topic] if article.topic else [])
    return {
        "id": article.id,
        "title": _clean_display_text(article.title),
        "source": _clean_display_text(article.source),
        "description": _clean_display_text(article.summary or article.description or ""),
        "date": date_str,
        "trustScore": article.trust_score if article.trust_version == SCORE_VERSION else None,
        "category": article.topic,
        "categories": categories,
        "image": article.image_url or None,
        "imageStored": bool(article.image_url and image_cache.cached(article.image_url)),
        "url": article.url,
        "author": article.author,
        "sentiment": article.sentiment,
        "toneLabel": getattr(article, "tone_label", None),
        "sentimentScore": article.sentiment_score,
        "trustLabel": article.trust_label,
        "trustExplanation": article.trust_explanation,
        "trustComponents": article.trust_components,
        "trustWeights": article.trust_weights,
        "relatedReports": article.trust_evidence,
        "contentChecks": article.trust_content_checks,
        "storyId": article.story_id or article.id,
        "threadId": article.thread_id or article.story_id or article.id,
        "trustVersion": article.trust_version,
        "trustScoredAt": article.trust_scored_at.isoformat() + "Z" if article.trust_scored_at else None
    } if detail else _list_fields(article)


# Fields a news card, search result or ranking needs. The detailed trust
# evidence is left out of lists (it made the feed about 1 MB) and is loaded
# with the article page instead (GET /api/articles/{id}).
_DETAIL_ONLY = ("trustExplanation", "trustComponents", "trustWeights", "relatedReports", "contentChecks", "trustVersion",
                "trustScoredAt", "sentimentScore")


async def _list_with_updates(articles) -> list:
    """News-card fields, plus how many updates each article's developing story
    has in total (the feed only holds the latest articles, so it cannot count
    older updates itself)."""
    counts = await storage_service.count_thread_updates({a.thread_id for a in articles if a.thread_id})
    items = []
    for article in articles:
        item = _article_to_feed_dict(article, detail=False)
        if counts.get(article.thread_id, 0) > 1:
            item["threadUpdates"] = counts[article.thread_id]
        items.append(item)
    return items


def _list_fields(article) -> dict:
    full = _article_to_feed_dict(article, detail=True)
    for key in _DETAIL_ONLY:
        full.pop(key, None)
    return full


# The feed only changes when the news worker saves or rescores articles, so the
# prepared response is kept until then. Browsers revalidate with the ETag and
# receive "304 Not Modified" (no body) when nothing has changed.
_feed_cache = {}


def _feed_response(request: Request, body: bytes, etag: str) -> Response:
    headers = {"ETag": etag, "Cache-Control": "private, no-cache"}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return Response(content=body, media_type="application/json", headers=headers)


@app.get("/api/articles/feed")
async def get_feed(request: Request, user=Depends(get_current_user), topic: str = None,
                   limit: int = Query(50, ge=1, le=1000)):
    """Get the latest news feed, sourced from the MongoDB-backed article
    store that the background news worker keeps up to date (configured Malaysia English RSS feeds).
    The response is the same for every reader, so it is prepared once per
    change of the article store and served from memory."""
    key = (topic or "all", limit)
    # which database, how many changes so far, and a 5-minute safety limit
    version = (id(storage_service.articles), storage_service.articles_version, int(time.monotonic() // 300))
    cached = _feed_cache.get(key)
    if not cached or cached[0] != version:
        articles = await storage_service.get_latest_articles(limit=limit, topic=topic)
        total = await storage_service.count_articles()
        payload = {
            "articles": await _list_with_updates(articles),
            "total_articles_in_db": total,
            "last_fetch_run": news_worker.last_run_stats or None,
        }
        body = json.dumps(jsonable_encoder(payload), separators=(",", ":")).encode()
        etag = '"' + hashlib.sha1(body).hexdigest()[:20] + '"'
        if len(_feed_cache) > 20:
            _feed_cache.clear()
        cached = _feed_cache[key] = (version, body, etag)
    return _feed_response(request, cached[1], cached[2])


@app.get("/api/articles/search")
async def search_articles(q: str = Query(..., min_length=2, max_length=100), limit: int = Query(100, ge=1, le=200),
                          user=Depends(get_current_user)):
    """Search every stored article (not only the latest batch) by headline,
    summary or publisher, newest first."""
    articles = await storage_service.search_articles(q, limit=limit, publishers=_followed_names(user))
    total = await storage_service.count_search(q, _followed_names(user))
    return {"articles": await _list_with_updates(articles), "query": q, "total": total}


@app.get("/api/articles/suggest")
async def suggest_keywords(q: str = Query("", max_length=60), user=Depends(get_current_user)):
    """Keyword suggestions for the search box: completions of what is typed,
    or trending topics of the last two days when the box is empty. Every
    suggestion is checked with the real search, limited to the user's
    followed publishers, so its count is exactly what the search shows."""
    return await suggest.suggest(q, _followed_names(user))


refresh_jobs = {}
refresh_tasks = set()

async def _execute_refresh(job_id, platforms):
    try:
        stats = await news_worker.fetch_and_process_news(platforms)
        refresh_jobs[job_id].update(status="failed" if stats.get("error") else "completed", stats=stats)
    except asyncio.CancelledError:
        refresh_jobs[job_id].update(status="failed", message="Server stopped; refresh again.")
        raise
    except Exception:
        logger.exception("Refresh failed")
        refresh_jobs[job_id].update(status="failed", message="Refresh failed; please retry.")

@app.post("/api/articles/refresh", status_code=202)
async def refresh_articles(request: RefreshRequest, user=Depends(get_current_user)):
    if not request.platforms:
        raise HTTPException(status_code=400, detail="Select at least one platform.")
    for job_id, job in refresh_jobs.items():
        if job["owner"] == user.id and job["status"] == "pending":
            return {"jobId": job_id, "status": "pending"}
    # Bound process-local job history; unfinished jobs are retained.
    for old_id in list(refresh_jobs):
        if len(refresh_jobs) < 100:
            break
        if refresh_jobs[old_id]["status"] != "pending":
            del refresh_jobs[old_id]
    if len(refresh_jobs) >= 100:
        raise HTTPException(status_code=429, detail="Refresh queue is full; retry later.")
    job_id = uuid4().hex
    refresh_jobs[job_id] = {"owner": user.id, "status": "pending"}
    task = asyncio.create_task(_execute_refresh(job_id, request.platforms))
    refresh_tasks.add(task)
    task.add_done_callback(refresh_tasks.discard)
    return {"jobId": job_id, "status": "pending"}

@app.get("/api/articles/refresh/{job_id}")
async def refresh_status(job_id: str, user=Depends(get_current_user)):
    job = refresh_jobs.get(job_id)
    if not job or job["owner"] != user.id:
        raise HTTPException(status_code=404, detail="Refresh job not found")
    return {key: value for key, value in job.items() if key != "owner"}

@app.get("/api/articles/{article_id}")
async def article_detail(article_id: str, user=Depends(get_current_user)):
    article = await storage_service.get_article_by_id(article_id)
    if not article or article.processing_status != "completed":
        raise HTTPException(status_code=404, detail="Article not found")
    detail = _article_to_feed_dict(article)
    detail.update(await _story_comparison(article))
    detail["timeline"] = await _story_timeline(article)
    return detail


async def _story_timeline(article) -> list:
    """A developing story's updates, oldest first: one entry per story with its
    time, headline (best-scored version) and the publishers that reported it."""
    if not article.thread_id:
        return []
    members = await storage_service.get_articles_by_thread(article.thread_id)
    stories = {}
    for member in members:
        stories.setdefault(member.story_id or member.id, []).append(member)
    if len(stories) < 2:
        return []
    timeline = []
    for story_id, versions in stories.items():
        lead = max(versions, key=lambda v: (v.trust_score or 0, -v.published_date.timestamp()))
        first = min(versions, key=lambda v: v.published_date)
        sources = []
        for v in sorted(versions, key=lambda v: v.published_date):
            name = _clean_display_text(v.source)
            if name not in sources:
                sources.append(name)
        timeline.append({"storyId": story_id, "id": lead.id, "title": _clean_display_text(lead.title),
                         "date": _article_to_feed_dict(first, detail=False)["date"], "sources": sources,
                         "current": any(v.id == article.id for v in versions)})
    return sorted(timeline, key=lambda entry: entry["date"])


async def _story_comparison(article) -> dict:
    """The other publishers' versions of this story, and what each version
    mentions that the others do not (numbers, quotes, names)."""
    versions = await storage_service.get_articles_by_story(article.story_id) if article.story_id else []
    if not any(v.id == article.id for v in versions):
        versions.append(article)
    if len(versions) < 2:
        return {"storyVersions": [], "uniqueDetails": []}
    details = story_grouper.distinctive_details({v.id: story_grouper.version_text(v) for v in versions})
    first = min(versions, key=lambda v: v.published_date).id
    def summary(v):
        return {"id": v.id, "title": _clean_display_text(v.title), "source": _clean_display_text(v.source),
                "date": _article_to_feed_dict(v, detail=False)["date"], "url": v.url,
                "trustScore": v.trust_score if v.trust_version == SCORE_VERSION else None,
                "trustLabel": v.trust_label, "sentiment": v.sentiment, "toneLabel": v.tone_label,
                "uniqueDetails": details.get(v.id, []), "first": v.id == first}
    return {"storyVersions": [summary(v) for v in versions if v.id != article.id],
            "uniqueDetails": details.get(article.id, []), "reportedFirst": article.id == first}


@app.get("/api/articles/{article_id}/image")
async def article_image(article_id: str):
    """Serve the locally stored copy of an article's image.

    Public because <img> tags cannot send the bearer token; only images of
    stored articles are served, never arbitrary URLs."""
    article = await storage_service.get_article_by_id(article_id)
    if not article or article.processing_status != "completed" or not article.image_url:
        raise HTTPException(status_code=404, detail="Image not found")
    hit = image_cache.cached(article.image_url)
    if not hit and await asyncio.to_thread(image_cache.download, article.image_url):
        hit = image_cache.cached(article.image_url)
    if not hit:
        raise HTTPException(status_code=404, detail="Image not available")
    path, content_type = hit
    return FileResponse(path, media_type=content_type, headers={"Cache-Control": "public, max-age=86400"})


# ---------------------------------------------------------------------------
# Email notification endpoints
# ---------------------------------------------------------------------------

@app.get("/api/notifications/email/status")
async def email_status(user=Depends(get_current_user)):
    """Return the current user's email notification settings and whether the
    server has SMTP credentials configured."""
    return {
        "email": user.email,
        "email_notifications_enabled": getattr(user, "email_notifications_enabled", False),
        "email_notification_schedule": getattr(user, "email_notification_schedule", "morning") or "morning",
        "email_notification_times": user_times(user),
        "email_verified": bool(getattr(user, "email_verified", False)),
        "max_notification_times": MAX_TIMES,
        "timezone": settings.EMAIL_TIMEZONE,
        "server_configured": email_service.is_configured()
    }


@app.put("/api/notifications/email", response_model=UserResponse)
async def update_email_settings(settings_update: EmailSettingsUpdate, user=Depends(get_current_user)):
    """Update the current user's email notification toggle and/or schedule
    delivery times (one to three HH:MM times in Malaysian time; the legacy
    morning/night/both presets are still accepted)."""
    update_data = {}

    if settings_update.email_notification_schedule is not None:
        schedule = settings_update.email_notification_schedule.strip().lower()
        if schedule not in VALID_EMAIL_SCHEDULES:
            raise HTTPException(
                status_code=400,
                detail="email_notification_schedule must be one of: morning, night, both"
            )
        update_data["email_notification_schedule"] = schedule
        update_data["email_notification_times"] = LEGACY_PRESETS[schedule]

    if settings_update.email_notification_times is not None:
        try:
            update_data["email_notification_times"] = normalize_times(settings_update.email_notification_times)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    if settings_update.email_notifications_enabled is not None:
        update_data["email_notifications_enabled"] = settings_update.email_notifications_enabled

    if update_data:
        user = await storage_service.update_user_by_email(user.email, update_data)

    return _user_to_response(user)


@app.post("/api/notifications/email/test")
async def send_email_test(payload: EmailTestMessage = None, user=Depends(get_current_user)):
    """Send a notification email to the current user's account email right now.
    Requires a verified address and is limited to one send per minute."""
    if not getattr(user, "email_verified", False):
        raise HTTPException(status_code=403, detail="Verify your email address before sending notifications.")
    now = datetime.utcnow()
    wait = email_verification.wait_seconds(user.last_on_demand_email_at, email_verification.SEND_NOW_COOLDOWN, now)
    if wait:
        raise HTTPException(status_code=429, detail=f"Please wait {wait} seconds before sending another notification.")
    await storage_service.update_user_by_email(user.email, {"last_on_demand_email_at": now})
    result = await _send_digest_email_to_user(user, period_label="On-Demand", custom_message=(payload.message if payload else None))

    if not result["success"]:
        raise HTTPException(status_code=502, detail=result["message"])

    return {"status": "sent", "detail": result["message"]}


@app.post("/api/notifications/email/verification")
async def send_verification_code(user=Depends(get_current_user)):
    """Email a 6-digit code to the account address to prove ownership."""
    if getattr(user, "email_verified", False):
        raise HTTPException(status_code=400, detail="Your email address is already verified.")
    now = datetime.utcnow()
    state = dict(getattr(user, "email_verification", None) or {})
    allowed, reason = email_verification.can_send_code(state, now)
    if not allowed:
        raise HTTPException(status_code=429, detail=reason)
    code = email_verification.new_code()
    message = email_verification.build_code_email(user.name, code, site_url=settings.site_url)
    result = await asyncio.to_thread(
        email_service.send_email, user.email, message["subject"], message["text"], message["html"])
    if not result["success"]:
        raise HTTPException(status_code=502, detail=result["message"])
    await storage_service.update_user_by_email(
        user.email, {"email_verification": email_verification.record_code(state, user.email, code, now)})
    return {"status": "sent", "detail": "A verification code was sent to your email address."}


@app.post("/api/notifications/email/verification/confirm", response_model=UserResponse)
async def confirm_verification_code(payload: EmailVerificationConfirm, user=Depends(get_current_user)):
    """Confirm the emailed code and mark the address as verified."""
    if getattr(user, "email_verified", False):
        return _user_to_response(user)
    state = dict(getattr(user, "email_verification", None) or {})
    result, new_state = email_verification.check_code(state, user.email, payload.code, datetime.utcnow())
    if result == "ok":
        user = await storage_service.update_user_by_email(
            user.email, {"email_verified": True, "email_verification": new_state})
        return _user_to_response(user)
    if result == "wrong":
        await storage_service.update_user_by_email(user.email, {"email_verification": new_state})
    detail = {
        "missing": "Request a verification code first.",
        "expired": "This code has expired. Request a new one.",
        "locked": "Too many incorrect attempts. Request a new code.",
        "wrong": "Incorrect code. Please check the email and try again.",
    }[result]
    raise HTTPException(status_code=429 if result == "locked" else 400, detail=detail)


MAX_DIGEST_ARTICLES = 10


async def _send_digest_email_to_user(user, period_label: str = "", custom_message: Optional[str] = None) -> dict:
    """Build and send a personalized news digest email to a single user,
    using up to ten articles, prioritizing preferred topics and filling
    remaining slots from recent articles."""
    preferred_topics = getattr(user, "preferred_topics", None) or []
    
    logger.info(f"Preparing email digest for {user.email}, preferred topics: {preferred_topics}")

    # First try to get articles from user's preferred topics
    articles = []
    if preferred_topics:
        removed_topics = {"Education", "Lifestyle", "Property", "Malaysia", "World"}
        allowed_topics = [topic for topic in preferred_topics if topic not in removed_topics]
        articles = from_followed(await storage_service.get_latest_articles_for_topics(
            allowed_topics, limit=MAX_DIGEST_ARTICLES * 4
        ), getattr(user, "followed_platforms", None))
        logger.info(f"Found {len(articles)} articles from preferred topics for {user.email}")
    
    # Slots are counted in stories (one story's versions share one entry).
    def stories_in(items):
        return len({a.thread_id or a.story_id or a.id for a in items})

    # If not enough articles from preferred topics, fall back to all latest articles
    if stories_in(articles) < MAX_DIGEST_ARTICLES:
        all_articles = from_followed(await storage_service.get_latest_articles(limit=MAX_DIGEST_ARTICLES * 4),
                                     getattr(user, "followed_platforms", None))
        # Prioritize articles from user's topics if they exist
        if preferred_topics:
            # Add any additional articles from topics that weren't already included
            for article in all_articles:
                if article not in articles:
                    articles.append(article)
                    if stories_in(articles) >= MAX_DIGEST_ARTICLES:
                        break
        else:
            articles = all_articles
        logger.info(f"After fallback: {len(articles)} articles for {user.email}")
    
    # At most ten articles, depending on availability
    # One entry per story: the best-scored version, naming the other publishers.
    digest_articles = []
    for story in story_grouper.combine_by_story(articles)[:MAX_DIGEST_ARTICLES]:
        entry = _article_to_feed_dict(story["article"])
        entry["alsoReportedBy"] = [_clean_display_text(name) for name in story["also_reported_by"]]
        entry["updates"] = story["updates"]
        digest_articles.append(entry)
    logger.info(f"Sending email digest with {len(digest_articles)} articles to {user.email}")

    digest = email_service.build_news_digest_email(
        user.name, digest_articles, period_label=period_label, site_url=settings.site_url)
    text_body = digest["text"]
    if custom_message:
        text_body = f"{custom_message}\n\n{text_body}"

    # Run the blocking SMTP call in a worker thread so it never blocks the
    # async event loop (important for the scheduled digest jobs that may
    # email many users in one run).
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: email_service.send_email(
            to_email=user.email,
            subject=digest["subject"],
            body_text=text_body,
            body_html=digest["html"]
        )
    )


# ---------------------------------------------------------------------------
# Scheduled email notifications (up to three custom times per user)
# ---------------------------------------------------------------------------

email_scheduler = AsyncIOScheduler()
FRESH_NEWS_MAX_AGE = timedelta(minutes=10)


async def _refresh_news_if_stale():
    """Fetch the latest articles before a digest unless a run just finished.
    Overnight (automatic collection paused) digests use the stored articles."""
    from app.worker import in_quiet_hours
    if in_quiet_hours():
        return
    last = news_worker.last_run_at
    try:
        if last and datetime.utcnow() - datetime.fromisoformat(last) < FRESH_NEWS_MAX_AGE:
            return
    except ValueError:
        pass
    try:
        stats = await news_worker.fetch_and_process_news()
        logger.info(f"News refresh before digest emails completed: {stats}")
    except Exception as exc:
        logger.error(f"News refresh before digest emails failed, sending with existing articles: {exc}", exc_info=True)


async def _run_due_email_notifications(now: Optional[datetime] = None):
    """Runs every minute. Sends one digest to each opted-in user whose
    delivery time has just been reached and was not yet sent today."""
    from zoneinfo import ZoneInfo
    from app.models.user import UserInDB
    now = now or datetime.now(ZoneInfo(settings.EMAIL_TIMEZONE))
    try:
        due = []
        async for doc in storage_service.users.find({"email_notifications_enabled": True, "email_verified": True}):
            doc["_id"] = str(doc["_id"])
            user = UserInDB(**doc)
            slots = due_times(user, now)
            if slots:
                due.append((user, slots))
        if not due:
            return 0
        await _refresh_news_if_stale()
        count = 0
        today = now.date().isoformat()
        for user, slots in due:
            label = "Morning" if now.hour < 12 else "Afternoon" if now.hour < 18 else "Evening"
            result = await _send_digest_email_to_user(user, period_label=label)
            if result["success"]:
                count += 1
                sent = dict(user.email_notification_last_sent or {})
                sent.update({slot: today for slot in slots})
                await storage_service.update_user_by_email(user.email, {"email_notification_last_sent": sent})
            else:
                logger.warning(f"Failed to send scheduled email to {user.email}: {result['message']}")
        logger.info(f"Scheduled digest emails sent to {count} of {len(due)} due user(s).")
        return count
    except Exception as exc:
        logger.error(f"Error running scheduled email notifications: {exc}", exc_info=True)
        return 0


def start_email_scheduler():
    """One job checks every minute, in explicit Malaysian time, which users
    are due for their custom delivery times."""
    if email_scheduler.running:
        return
    email_scheduler.add_job(
        _run_due_email_notifications,
        CronTrigger(minute="*", timezone=settings.EMAIL_TIMEZONE),
        id="email_due_check_job", replace_existing=True,
        coalesce=True, max_instances=1, misfire_grace_time=60)
    email_scheduler.start()
