from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncio
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
from app.services import email_service, image_cache
from app.services.trust_scorer import SCORE_VERSION
from app.services.notification_times import LEGACY_PRESETS, MAX_TIMES, due_times, normalize_times, user_times
from app.services.storage import storage_service
from app.core.security import get_password_hash, verify_password, create_access_token
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
        print("MongoDB indexes ensured. User accounts will persist across restarts.")
    except Exception as exc:
        print(f"Warning: could not ensure MongoDB indexes: {exc}")

    try:
        await storage_service.seed_source_credibility()
        print("Source credibility scores seeded (used for trust score calculation).")
    except Exception as exc:
        print(f"Warning: could not seed source credibility: {exc}")

    try:
        start_email_scheduler()
        print("Email notification scheduler started (checks custom delivery times every minute).")
    except Exception as exc:
        print(f"Warning: could not start email scheduler: {exc}")

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
    message: Optional[str] = None


def _user_to_response(user) -> UserResponse:
    """Convert a UserInDB (MongoDB-backed) model into the API UserResponse."""
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        preferred_topics=user.preferred_topics or [],
        email_notifications_enabled=getattr(user, "email_notifications_enabled", False),
        email_notification_schedule=getattr(user, "email_notification_schedule", "morning") or "morning",
        email_notification_times=user_times(user)
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
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete account. Please try again.")

    return {"status": "deleted", "detail": "Your account has been permanently deleted."}

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

def _article_to_feed_dict(article) -> dict:
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
        "trustVersion": article.trust_version,
        "trustScoredAt": article.trust_scored_at.isoformat() + "Z" if article.trust_scored_at else None
    }


@app.get("/api/articles/feed")
async def get_feed(user=Depends(get_current_user), topic: str = None, limit: int = Query(50, ge=1, le=1000)):
    """Get the latest news feed, sourced from the MongoDB-backed article
    store that the background news worker keeps up to date (configured Malaysia English RSS feeds)."""
    articles = await storage_service.get_latest_articles(limit=limit, topic=topic)
    total = await storage_service.count_articles()

    return {
        "articles": [_article_to_feed_dict(a) for a in articles],
        "total_articles_in_db": total,
        "last_fetch_run": news_worker.last_run_stats or None
    }


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
    return _article_to_feed_dict(article)


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
    """Send a notification email to the current user's account email right now."""
    result = await _send_digest_email_to_user(user, period_label="On-Demand", custom_message=(payload.message if payload else None))

    if not result["success"]:
        raise HTTPException(status_code=502, detail=result["message"])

    return {"status": "sent", "detail": result["message"]}


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
        articles = await storage_service.get_latest_articles_for_topics(
            allowed_topics, limit=MAX_DIGEST_ARTICLES * 2
        )
        logger.info(f"Found {len(articles)} articles from preferred topics for {user.email}")
    
    # If not enough articles from preferred topics, fall back to all latest articles
    if len(articles) < MAX_DIGEST_ARTICLES:
        all_articles = await storage_service.get_latest_articles(limit=MAX_DIGEST_ARTICLES * 2)
        # Prioritize articles from user's topics if they exist
        if preferred_topics:
            # Add any additional articles from topics that weren't already included
            for article in all_articles:
                if article not in articles:
                    articles.append(article)
                    if len(articles) >= MAX_DIGEST_ARTICLES:
                        break
        else:
            articles = all_articles
        logger.info(f"After fallback: {len(articles)} articles for {user.email}")
    
    # At most ten articles, depending on availability
    digest_articles = [_article_to_feed_dict(a) for a in articles[:MAX_DIGEST_ARTICLES]]
    logger.info(f"Sending email digest with {len(digest_articles)} articles to {user.email}")

    digest = email_service.build_news_digest_email(user.name, digest_articles, period_label=period_label)
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
    """Fetch the latest articles before a digest unless a run just finished."""
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
        async for doc in storage_service.users.find({"email_notifications_enabled": True}):
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
