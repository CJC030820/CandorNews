from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ArticleBase(BaseModel):
    title: str
    author: Optional[str] = None
    source: str
    url: str
    published_date: datetime
    description: Optional[str] = None
    content_excerpt: Optional[str] = None
    image_url: Optional[str] = None
    topic: str  # Primary category (first entry of `topics`), kept for backward compatibility
    topics: List[str] = []  # Up to 3 categories, ranked by relevance
    summary: Optional[str] = None
    keywords: List[str] = []
    sentiment: str  # Positive, Neutral, Negative
    sentiment_score: Optional[float] = None
    tone_label: Optional[str] = None  # Neutral / Objective, Mildly Emotional, Emotionally Charged
    trust_score: float  # 0-100
    trust_explanation: Optional[str] = None
    processing_status: str = "pending"  # pending, completed, failed
    processed_at: Optional[datetime] = None

class ArticleCreate(ArticleBase):
    pass

class ArticleInDB(ArticleBase):
    id: str = Field(alias="_id")

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ArticleResponse(ArticleBase):
    id: str

    class Config:
        allow_population_by_field_name = True