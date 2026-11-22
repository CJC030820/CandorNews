from pathlib import Path
import secrets
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings

# Resolve backend/.env relative to this file so settings load regardless of
# the directory uvicorn is launched from.
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    # MongoDB settings
    MONGODB_URL: str = "mongodb://mongodb:27017"
    DATABASE_NAME: str = "news_intelligence"

    # JWT settings
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    ENVIRONMENT: str = "development"
    EMAIL_TIMEZONE: str = "Asia/Kuala_Lumpur"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    # Public address of the website, used for links in emails. When empty,
    # the first CORS origin is used (the site's own https address in production).
    PUBLIC_SITE_URL: str = ""

    @property
    def site_url(self) -> str:
        url = self.PUBLIC_SITE_URL or self.CORS_ORIGINS.split(",")[0]
        return url.strip().rstrip("/")

    @model_validator(mode="after")
    def validate_deployment_secret(self):
        if self.ENVIRONMENT == "production" and ("SECRET_KEY" not in self.model_fields_set or len(self.SECRET_KEY) < 32 or "dev-secret" in self.SECRET_KEY):
            raise ValueError("Production requires an explicit strong SECRET_KEY of at least 32 characters")
        return self
    ALGORITHM: str = "HS256"
    # Long-lived session so users stay logged in ("remember me") across
    # browser restarts and backend restarts, as long as the token itself
    # (stored in localStorage) is still present.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days

    # News API keys (example)
    NEWSAPI_KEY: str = ""
    GNEWS_API_KEY: str = ""

    # RSS feeds - Malaysia English news sources only
    RSS_FEEDS: str = "https://www.freemalaysiatoday.com/feed/,https://www.freemalaysiatoday.com/category/nation/feed/,https://www.freemalaysiatoday.com/category/business/feed/,https://www.freemalaysiatoday.com/category/world/feed/,https://www.nst.com.my/feed,https://www.bernama.com/en/rssfeed.php,https://www.malaymail.com/feed/rss/malaysia,https://thesun.my/news/feed/"

    # The versioned heuristic weights are defined in services/trust_scorer.py.

    # Worker interval in minutes
    WORKER_INTERVAL_MINUTES: int = 15
    # Automatic news collection pauses overnight (hours in EMAIL_TIMEZONE, Malaysia time).
    # The "Refresh News" button still works during these hours.
    NEWS_QUIET_START_HOUR: int = 0
    NEWS_QUIET_END_HOUR: int = 6

    class Config:
        env_file = str(_ENV_FILE)
        # SMTP_* and other env vars are consumed by other modules but not
        # declared on Settings; allow them to flow through without validation.
        extra = "ignore"

settings = Settings()