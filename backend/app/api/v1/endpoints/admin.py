from fastapi import APIRouter, Depends, HTTPException, status
from app.services.worker import news_worker
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
    # In a real app, we would check if the user is an admin
    # For now, we'll allow any authenticated user to trigger admin actions (for simplicity)
    user = await storage_service.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@router.post("/fetch-news", response_model=dict)
async def trigger_news_fetch(
    current_user: UserResponse = Depends(get_current_user)
):
    # Trigger the background worker to fetch news immediately
    # In a production system, we might want to use a task queue like Celery
    # For now, we'll call the async function directly (but note: this is a blocking call)
    import asyncio
    try:
        # Since we're in a sync endpoint, we'll run the async function in an event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(news_worker.fetch_and_process_news())
        loop.close()
        return {"message": "News fetch triggered successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger news fetch: {str(e)}"
        )

@router.post("/reprocess-articles", response_model=dict)
async def trigger_reprocess_articles(
    current_user: UserResponse = Depends(get_current_user)
):
    # Placeholder for reprocessing articles (e.g., update trust scores, etc.)
    return {"message": "Article reprocessing triggered (not implemented)"}
