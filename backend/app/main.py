from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta, timezone
from typing import Optional
import os
import logging
from pydantic import BaseModel
from jose import JWTError, jwt
import ldclient
from ldclient.config import Config
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Import the LD utils
from app.utils.ld_utils import get_flag
from app.services import email_service
from app.services.storage import storage_service
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings
from app.models.user import UserCreate as DBUserCreate
from app.worker import news_worker

logger = logging.getLogger(__name__)

VALID_EMAIL_SCHEDULES = {"morning", "night", "both"}

# JWT settings (kept in sync with app/core/security.py via settings)
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# Initialize LaunchDarkly client
ld_sdk_key = os.getenv("LD_SDK_KEY", "")
ld_client = None
if ld_sdk_key and "your" not in ld_sdk_key.lower() and ld_sdk_key != "your-flag-key-here":
    try:
        ldclient.set_config(Config(ld_sdk_key))
        ld_client = ldclient.get()
    except Exception as exc:
        print(f"Warning: failed to initialize LaunchDarkly client: {exc}")
        ld_client = None

def get_ld_client():
    return ld_client

app = FastAPI(
    title="Trust-Aware Personalized AI News Intelligence System",
    description="API for the news intelligence system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    """Ensure database indexes exist so accounts persist reliably, start the
    scheduled email notification jobs (7am and 7pm), and start the background
    news ingestion worker that fetches the latest headlines from NewsAPI,
    GNews, and RSS feeds (runs immediately, then every WORKER_INTERVAL_MINUTES)."""
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
        print("Email notification scheduler started (7am and 7pm daily).")
    except Exception as exc:
        print(f"Warning: could not start email scheduler: {exc}")

    try:
        news_worker.start()
        print("News ingestion worker started (fetching latest news in the background).")
    except Exception as exc:
        print(f"Warning: could not start news ingestion worker: {exc}")


@app.on_event("shutdown")
async def on_shutdown():
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
    email: str
    password: str
    name: str

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

class UserProfileUpdate(BaseModel):
    name: str

class AccountDeleteRequest(BaseModel):
    password: str

class EmailSettingsUpdate(BaseModel):
    email_notifications_enabled: Optional[bool] = None
    email_notification_schedule: Optional[str] = None

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
        email_notification_schedule=getattr(user, "email_notification_schedule", "morning") or "morning"
    )


async def get_current_user(token: str = None):
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

    new_user = await storage_service.create_user(
        DBUserCreate(
            name=user.name,
            email=user.email,
            password=user.password,
            preferred_topics=[],
            email_notifications_enabled=False,
            email_notification_schedule="morning"
        )
    )

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
async def get_current_user_info(token: str = None):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await get_current_user(token)
    return _user_to_response(user)

@app.put("/api/users/preferences")
async def update_preferences(preferences: dict, token: str = None):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await get_current_user(token)
    updated_user = await storage_service.update_user_by_email(
        user.email,
        {"preferred_topics": preferences.get("preferred_topics", [])}
    )

    return _user_to_response(updated_user)


@app.put("/api/users/profile", response_model=UserResponse)
async def update_profile(profile: UserProfileUpdate, token: str = None):
    """Update the current user's display name. Persisted permanently in
    MongoDB, so the new name survives server restarts and future logins."""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    new_name = profile.name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Name cannot be empty.")

    user = await get_current_user(token)
    updated_user = await storage_service.update_user_by_email(
        user.email,
        {"name": new_name}
    )

    return _user_to_response(updated_user)


@app.delete("/api/users/me")
async def delete_account(request: AccountDeleteRequest, token: str = None):
    """Permanently delete the current user's account. Requires the account
    password to be re-entered as a safety confirmation. This action cannot
    be undone - the user document is removed from MongoDB entirely."""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await get_current_user(token)

    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect password.")

    deleted = await storage_service.delete_user_by_email(user.email)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete account. Please try again.")

    return {"status": "deleted", "detail": "Your account has been permanently deleted."}

def _article_to_feed_dict(article) -> dict:
    """Convert a stored ArticleInDB into the shape the frontend expects."""
    published = article.published_date
    date_str = published.isoformat() if hasattr(published, "isoformat") else str(published)
    categories = getattr(article, "topics", None) or ([article.topic] if article.topic else [])
    return {
        "id": article.id,
        "title": article.title,
        "source": article.source,
        "description": article.summary or article.description or "",
        "date": date_str,
        "trustScore": round(article.trust_score) if article.trust_score is not None else None,
        "category": article.topic,
        "categories": categories,
        "image": article.image_url or None,
        "url": article.url,
        "author": article.author,
        "sentiment": article.sentiment,
        "toneLabel": getattr(article, "tone_label", None)
    }


@app.get("/api/articles/feed")
async def get_feed(token: str = None, topic: str = None, limit: int = 50):
    """Get the latest news feed, sourced from the MongoDB-backed article
    store that the background news worker keeps up to date (NewsAPI, GNews,
    and Malaysia English RSS feeds)."""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Validate the token (raises 401 if invalid)
    await get_current_user(token)

    articles = await storage_service.get_latest_articles(limit=limit, topic=topic)
    total = await storage_service.count_articles()

    return {
        "articles": [_article_to_feed_dict(a) for a in articles],
        "total_articles_in_db": total,
        "last_fetch_run": news_worker.last_run_stats or None
    }


@app.post("/api/articles/refresh")
async def refresh_articles(token: str = None):
    """Manually trigger an on-demand fetch of the latest news right now,
    instead of waiting for the next scheduled background run."""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    await get_current_user(token)

    stats = await news_worker.fetch_and_process_news()
    return {"status": "completed", "stats": stats}


# ---------------------------------------------------------------------------
# Email notification endpoints
# ---------------------------------------------------------------------------

@app.get("/api/notifications/email/status")
async def email_status(token: str = None):
    """Return the current user's email notification settings and whether the
    server has SMTP credentials configured."""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await get_current_user(token)
    return {
        "email": user.email,
        "email_notifications_enabled": getattr(user, "email_notifications_enabled", False),
        "email_notification_schedule": getattr(user, "email_notification_schedule", "morning") or "morning",
        "server_configured": email_service.is_configured()
    }


@app.put("/api/notifications/email", response_model=UserResponse)
async def update_email_settings(settings_update: EmailSettingsUpdate, token: str = None):
    """Update the current user's email notification toggle and/or schedule
    preference (morning 7am / night 7pm / both)."""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await get_current_user(token)
    update_data = {}

    if settings_update.email_notification_schedule is not None:
        schedule = settings_update.email_notification_schedule.strip().lower()
        if schedule not in VALID_EMAIL_SCHEDULES:
            raise HTTPException(
                status_code=400,
                detail="email_notification_schedule must be one of: morning, night, both"
            )
        update_data["email_notification_schedule"] = schedule

    if settings_update.email_notifications_enabled is not None:
        update_data["email_notifications_enabled"] = settings_update.email_notifications_enabled

    if update_data:
        user = await storage_service.update_user_by_email(user.email, update_data)

    return _user_to_response(user)


@app.post("/api/notifications/email/test")
async def send_email_test(payload: EmailTestMessage = None, token: str = None):
    """Send a notification email to the current user's account email right now."""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await get_current_user(token)
    result = await _send_digest_email_to_user(user, period_label="On-Demand", custom_message=(payload.message if payload else None))

    if not result["success"]:
        raise HTTPException(status_code=502, detail=result["message"])

    return {"status": "sent", "detail": result["message"]}


MAX_DIGEST_ARTICLES = 10


async def _send_digest_email_to_user(user, period_label: str = "", custom_message: Optional[str] = None) -> dict:
    """Build and send a personalized news digest email to a single user,
    using exactly 10 latest real articles matching their preferred topics.
    Falls back to the latest articles overall only if the user has no
    preferred topics set."""
    preferred_topics = getattr(user, "preferred_topics", None) or []
    
    logger.info(f"Preparing email digest for {user.email}, preferred topics: {preferred_topics}")

    # First try to get articles from user's preferred topics
    articles = []
    if preferred_topics:
        articles = await storage_service.get_latest_articles_for_topics(
            preferred_topics, limit=MAX_DIGEST_ARTICLES * 2  # Get more to ensure we have 10
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
    
    # Ensure exactly 10 articles
    digest_articles = [_article_to_feed_dict(a) for a in articles[:MAX_DIGEST_ARTICLES]]
    logger.info(f"Sending email digest with {len(digest_articles)} articles to {user.email}")

    digest = email_service.build_news_digest_email(user.name, digest_articles, period_label=period_label)
    text_body = digest["text"]
    if custom_message:
        text_body = f"{custom_message}\n\n{text_body}"

    # Run the blocking SMTP call in a worker thread so it never blocks the
    # async event loop (important for the scheduled 7am/7pm jobs that may
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
# Scheduled email notifications (7am morning / 7pm night)
# ---------------------------------------------------------------------------

email_scheduler = AsyncIOScheduler()


async def _run_scheduled_email_job(job_period: str):
    """Send digest emails to every user opted in for this time slot
    (morning, night, or both). Before sending, first triggers a fresh news
    fetch/refresh so users receive the latest articles at their preferred
    time instead of whatever was last cached from the periodic background
    worker run."""
    logger.info(f"Running scheduled email job: {job_period}")
    try:
        try:
            logger.info(f"Refreshing news before sending '{job_period}' digest emails...")
            refresh_stats = await news_worker.fetch_and_process_news()
            logger.info(f"News refresh before '{job_period}' digest completed: {refresh_stats}")
        except Exception as refresh_exc:
            logger.error(f"News refresh before '{job_period}' digest failed, sending with existing articles: {refresh_exc}", exc_info=True)

        cursor = storage_service.users.find({
            "email_notifications_enabled": True,
            "email_notification_schedule": {"$in": [job_period, "both"]}
        })
        count = 0
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            from app.models.user import UserInDB
            user = UserInDB(**doc)
            label = "Morning" if job_period == "morning" else "Evening"
            result = await _send_digest_email_to_user(user, period_label=label)
            if result["success"]:
                count += 1
            else:
                logger.warning(f"Failed to send scheduled email to {user.email}: {result['message']}")
        logger.info(f"Scheduled email job '{job_period}' completed. Sent to {count} user(s).")
    except Exception as exc:
        logger.error(f"Error running scheduled email job '{job_period}': {exc}", exc_info=True)


def start_email_scheduler():
    """Register the 7am / 7pm cron jobs and start the scheduler."""
    if email_scheduler.running:
        return

    # Wrap async job in sync function for APScheduler
    def run_morning_job():
        logger.info("Executing morning email job via scheduler")
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_run_scheduled_email_job("morning"))
        except Exception as e:
            logger.error(f"Morning job failed: {e}", exc_info=True)
        finally:
            loop.close()
    
    def run_evening_job():
        logger.info("Executing evening email job via scheduler")
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_run_scheduled_email_job("night"))
        except Exception as e:
            logger.error(f"Evening job failed: {e}", exc_info=True)
        finally:
            loop.close()
    
    email_scheduler.add_job(
        run_morning_job,
        CronTrigger(hour=7, minute=0),
        id="email_morning_job",
        replace_existing=True,
        name="Morning Email Digest"
    )
    email_scheduler.add_job(
        run_evening_job,
        CronTrigger(hour=19, minute=0),
        id="email_night_job",
        replace_existing=True,
        name="Evening Email Digest"
    )
    email_scheduler.start()


@app.get("/api/test-ld")
async def test_ld(
    ld_client = Depends(get_ld_client)
):
    """
    Test endpoint to verify LaunchDarkly client initialization.
    """
    if ld_client is None:
        return {"status": "error", "message": "LaunchDarkly client not initialized"}

    # Try to get a default flag value (this won't fail even if flag doesn't exist)
    try:
        # Create a test context
        context = {
            "key": "test-user",
            "email": "test@example.com"
        }

        # Try to get a flag that likely doesn't exist - should return default
        flag_value = ld_client.variation("test-flag-nonexistent", context, False)

        return {
            "status": "success",
            "message": "LaunchDarkly client is initialized and working",
            "client_initialized": ld_client.is_initialized(),
            "test_flag_value": flag_value
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error testing LaunchDarkly client: {str(e)}",
            "client_initialized": ld_client.is_initialized() if ld_client else False
        }


@app.get("/flags/{flag_key}")
async def get_feature_flag(
    flag_key: str,
    current_user = Depends(get_current_user),
    ld_client = Depends(get_ld_client)
):
    """
    Get the value of a feature flag for the current user.
    """
    # Create LD context
    context = {
        "key": str(current_user.id),
        "email": current_user.email,
        # Add any other attributes you want to target on
    }
    # Default to False if flag not found or error
    flag_value = get_flag(ld_client, context, flag_key, False)
    return {"flag_key": flag_key, "value": flag_value}


@app.get("/test-ld")
async def test_ld_connection():
    """
    Test endpoint to check if LaunchDarkly client is initialized.
    """
    if ld_client is None:
        return {
            "status": "error",
            "message": "LaunchDarkly client is not initialized. Check LD_SDK_KEY environment variable."
        }

    try:
        # Try to get a flag value (this will use default if flag doesn't exist)
        test_context = {
            "key": "test-user",
            "email": "test@example.com"
        }
        flag_value = ld_client.variation("test-flag", test_context, False)

        return {
            "status": "success",
            "message": "LaunchDarkly client is initialized and working",
            "is_initialized": ld_client.is_initialized(),
            "test_flag_value": flag_value
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error testing LaunchDarkly client: {str(e)}",
            "is_initialized": ld_client.is_initialized() if ld_client else False
        }
