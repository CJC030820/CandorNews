from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.models.article import ArticleResponse
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

@router.post("/{article_id}", response_model=dict)
async def bookmark_article(
    article_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    # Check if article exists and is completed
    article = await storage_service.get_article_by_id(article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found"
        )
    if article.processing_status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Article is not available for bookmarking"
        )
    # Check if already bookmarked
    existing = await storage_service.get_interactions_by_user_and_article(
        current_user.id, article_id
    )
    # Check if any interaction is a bookmark
    is_bookmarked = any(interaction.action_type == "bookmark" for interaction in existing)
    if is_bookmarked:
        return {"message": "Article already bookmarked"}
    # Create bookmark interaction
    from app.models.interaction import InteractionCreate
    interaction = InteractionCreate(
        user_id=current_user.id,
        article_id=article_id,
        action_type="bookmark"
    )
    await storage_service.create_interaction(interaction)
    return {"message": "Article bookmarked successfully"}

@router.delete("/{article_id}", response_model=dict)
async def remove_bookmark(
    article_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    # Find bookmark interaction and delete it
    interactions = await storage_service.get_interactions_by_user_and_article(
        current_user.id, article_id
    )
    bookmark_interactions = [i for i in interactions if i.action_type == "bookmark"]
    if not bookmark_interactions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )
    # Delete the first bookmark interaction (assuming only one)
    from bson import ObjectId
    await storage_service.interactions.delete_one(
        {"_id": ObjectId(bookmark_interactions[0].id)}
    )
    return {"message": "Bookmark removed successfully"}

@router.get("/", response_model=List[ArticleResponse])
async def get_user_bookmarks(
    current_user: UserResponse = Depends(get_current_user)
):
    # Get all bookmark interactions for the user
    interactions = await storage_service.interactions.find({"user_id": current_user.id, "action_type": "bookmark"})
    article_ids = []
    async for interaction in interactions:
        article_ids.append(interaction["article_id"])
    # Fetch articles
    articles = []
    for article_id in article_ids:
        article = await storage_service.get_article_by_id(article_id)
        if article and article.processing_status == "completed":
            articles.append(article)
    return articles