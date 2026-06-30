from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from app.models.article import ArticleResponse
from app.models.user import User
from app.services.storage import storage_service
from app.core.security import decode_access_token
from fastapi.security import OAuth2PasswordBearer
from app.services.recommender import RecommenderService
from app.main import get_ld_client
from app.utils.ld_utils import get_flag

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
recommender_service = RecommenderService()

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

@router.get("/feed", response_model=List[ArticleResponse])
async def get_personalized_feed(
    limit: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user)
):
    # Get all completed articles
    articles = await storage_service.get_articles_by_status("completed")
    # Convert to list of dicts for recommender
    articles_dict = [article.dict() for article in articles]
    # Get personalized recommendations
    recommended = recommender_service.recommend_articles(
        current_user.id, articles_dict, limit
    )
    return recommended

@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    article = await storage_service.get_article_by_id(article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found"
        )
    # Only return completed articles
    if article.processing_status != "completed":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not available"
        )
    # Record interaction (view)
    from app.models.interaction import InteractionCreate
    interaction = InteractionCreate(
        user_id=current_user.id,
        article_id=article_id,
        action_type="view"
    )
    await storage_service.create_interaction(interaction)
    return article

@router.get("/", response_model=List[ArticleResponse])
async def search_articles(
    query: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user)
):
    # For simplicity, we'll just return all completed articles filtered by topic if provided
    articles = await storage_service.get_articles_by_status("completed")
    if topic:
        articles = [a for a in articles if a.topic == topic]
    if query:
        # Simple text search in title and description
        query_lower = query.lower()
        articles = [a for a in articles if
                   query_lower in a.title.lower() or
                   (a.description and query_lower in a.description.lower())]
    return articles[:limit]

@router.get("/trending/", response_model=List[ArticleResponse])
async def get_trending_articles(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user)
):
    # For now, trending = most recent articles
    articles = await storage_service.get_articles_by_status("completed")
    # Sort by published_date descending
    articles.sort(key=lambda x: x.published_date, reverse=True)
    return articles[:limit]

@router.get("/flags/{flag_key}")
async def get_feature_flag(
    flag_key: str,
    current_user: User = Depends(get_current_user),
    ld_client = Depends(get_ld_client)
):
    """
    Get the value of a feature flag for the current user.
    """
    # Create LD context
    context = {
        "key": str(current_user.id),
        "email": current_user.email,
        # Add any other attributes you want to target on
    }
    # Default to False if flag not found or error
    flag_value = get_flag(ld_client, context, flag_key, False)
    return {"flag_key": flag_key, "value": flag_value}