from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ArticleBase(BaseModel):
    title: str
    author: Optional[str] = None
    source: str
    url: str
    published_date: datetime
    publication_date_inferred: bool = False
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
    trust_label: Optional[str] = None
    trust_components: Dict[str, float] = Field(default_factory=dict)
    trust_weights: Dict[str, float] = Field(default_factory=dict)
    trust_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    trust_content_checks: List[Dict[str, Any]] = Field(default_factory=list)  # content_analyzer results
    story_id: Optional[str] = None  # shared by one story's versions from different publishers (story_grouper)
    trust_version: Optional[str] = None
    trust_scored_at: Optional[datetime] = None
    processing_status: str = "pending"  # pending, completed, failed
    processed_at: Optional[datetime] = None

class ArticleCreate(ArticleBase):
    pass

class ArticleInDB(ArticleBase):
    id: str = Field(alias="_id")

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ArticleResponse(ArticleBase):
    id: str

    class Config:
        populate_by_name = True