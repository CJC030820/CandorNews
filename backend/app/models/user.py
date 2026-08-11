from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class User(BaseModel):
    """MongoDB user document"""
    id: str = Field(alias="_id")
    email: str
    name: str
    hashed_password: str
    preferred_topics: List[str] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        allow_population_by_field_name = True

class UserBase(BaseModel):
    name: str
    email: str
    preferred_topics: List[str] = []
    email_notifications_enabled: bool = False
    # One of: "morning" (7am), "night" (7pm), "both" (7am and 7pm)
    email_notification_schedule: str = "morning"

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserInDB(UserBase):
    id: str = Field(alias="_id")
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserResponse(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        allow_population_by_field_name = True