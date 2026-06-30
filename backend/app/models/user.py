from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class UserBase(BaseModel):
    name: str
    email: str
    preferred_topics: List[str] = []

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