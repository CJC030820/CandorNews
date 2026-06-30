from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.schemas.auth import UserResponse
from app.services.storage import storage_service
from app.core.security import decode_access_token
from fastapi.security import OAuth2PasswordBearer

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await storage_service.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user: UserResponse = Depends(get_current_user)):
    return current_user

@router.put("/preferences", response_model=UserResponse)
async def update_preferences(
    preferred_topics: List[str],
    current_user: UserResponse = Depends(get_current_user)
):
    # Update user's preferred topics
    from bson import ObjectId
    await storage_service.users.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": {"preferred_topics": preferred_topics}}
    )
    # Fetch updated user
    updated_user = await storage_service.get_user_by_id(current_user.id)
    return updated_user