from fastapi import APIRouter, Depends, HTTPException, status
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

@router.post("/click/{article_id}", response_model=dict)
async def record_click(
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
            detail="Article is not available for interaction"
        )
    # Create click interaction
    from app.models.interaction import InteractionCreate
    interaction = InteractionCreate(
        user_id=current_user.id,
        article_id=article_id,
        action_type="click"
    )
    await storage_service.create_interaction(interaction)
    return {"message": "Click recorded successfully"}