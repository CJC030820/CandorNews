from pathlib import Path
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
    SECRET_KEY: str = "news-intelligence-static-dev-secret-key-do-not-use-in-prod"  # Change in production
    ALGORITHM: str = "HS256"
    # Long-lived session so users stay logged in ("remember me") across
    # browser restarts and backend restarts, as long as the token itself
    # (stored in localStorage) is still present.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days

    # News API keys (example)
    NEWSAPI_KEY: str = ""
    GNEWS_API_KEY: str = ""

    # RSS feeds - Malaysia English news sources only
    RSS_FEEDS: str = "https://www.freemalaysiatoday.com/feed/,https://www.freemalaysiatoday.com/category/nation/feed/,https://www.freemalaysiatoday.com/category/business/feed/,https://www.freemalaysiatoday.com/category/world/feed/,https://www.nst.com.my/feed,https://www.bernama.com/en/rssfeed.php"

    # Trust score weights (as per PRD)
    TRUST_WEIGHT_SOURCE_REPUTATION: float = 0.30
    TRUST_WEIGHT_CROSS_SOURCE: float = 0.25
    TRUST_WEIGHT_SEMANTIC_SIMILARITY: float = 0.20
    TRUST_WEIGHT_HEADLINE_CONSISTENCY: float = 0.15
    TRUST_WEIGHT_METADATA_COMPLETENESS: float = 0.10

    # Worker interval in minutes
    WORKER_INTERVAL_MINUTES: int = 30

    class Config:
        env_file = str(_ENV_FILE)
        # SMTP_* and other env vars are consumed by other modules but not
        # declared on Settings; allow them to flow through without validation.
        extra = "ignore"

settings = Settings()