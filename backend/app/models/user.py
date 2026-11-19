from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime

class User(BaseModel):
    """MongoDB user document"""
    id: str = Field(alias="_id")
    email: EmailStr
    name: str
    hashed_password: str
    preferred_topics: List[str] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True

class UserBase(BaseModel):
    name: str
    email: EmailStr
    preferred_topics: List[str] = []
    email_notifications_enabled: bool = False
    # Legacy preset: "morning" (7am), "night" (7pm), "both". Used only when no
    # custom times are stored.
    email_notification_schedule: str = "morning"
    # Up to three custom delivery times, "HH:MM" in EMAIL_TIMEZONE.
    email_notification_times: List[str] = []

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserInDB(UserBase):
    id: str = Field(alias="_id")
    hashed_password: str
    # Delivery time -> date (YYYY-MM-DD) it was last sent, so each time slot
    # is emailed at most once per day.
    email_notification_last_sent: dict = {}
    # Email ownership: digests are only sent once a code sent to this
    # address has been confirmed.
    email_verified: bool = False
    email_verification: dict = {}
    last_on_demand_email_at: Optional[datetime] = None
    # Publishers the user follows (ids from PLATFORMS); None = not chosen yet.
    followed_platforms: Optional[List[str]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserResponse(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True