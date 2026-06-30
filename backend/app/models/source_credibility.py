from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class SourceCredibilityBase(BaseModel):
    source_name: str
    domain: str
    credibility_score: float  # 0-100
    category: Optional[str] = None
    notes: Optional[str] = None

class SourceCredibilityCreate(SourceCredibilityBase):
    pass

class SourceCredibilityInDB(SourceCredibilityBase):
    id: str = Field(alias="_id")
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SourceCredibilityResponse(SourceCredibilityBase):
    id: str
    last_updated: datetime

    class Config:
        allow_population_by_field_name = True