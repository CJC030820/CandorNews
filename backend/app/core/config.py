from pydantic import BaseSettings

class Settings(BaseSettings):
    # MongoDB settings
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "news_intelligence"

    # JWT settings
    SECRET_KEY: str = "your-secret-key-here"  # Change in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # News API keys (example)
    NEWSAPI_KEY: str = ""
    GNEWS_API_KEY: str = ""

    # Trust score weights (as per PRD)
    TRUST_WEIGHT_SOURCE_REPUTATION: float = 0.30
    TRUST_WEIGHT_CROSS_SOURCE: float = 0.25
    TRUST_WEIGHT_SEMANTIC_SIMILARITY: float = 0.20
    TRUST_WEIGHT_HEADLINE_CONSISTENCY: float = 0.15
    TRUST_WEIGHT_METADATA_COMPLETENESS: float = 0.10

    class Config:
        env_file = ".env"

settings = Settings()