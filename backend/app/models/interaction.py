from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class InteractionBase(BaseModel):
    user_id: str
    article_id: str
    action_type: str  # click, bookmark, view
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class InteractionCreate(InteractionBase):
    pass

class InteractionInDB(InteractionBase):
    id: str = Field(alias="_id")

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class InteractionResponse(InteractionBase):
    id: str

    class Config:
        allow_population_by_field_name = True