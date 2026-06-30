from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import auth, users, articles, bookmarks, interactions, admin
from app.worker import news_worker
from datetime import datetime
from app.services.storage import storage_service

app = FastAPI(
    title="Trust-Aware Personalized AI News Intelligence System",
    description="API for the news intelligence system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(articles.router, prefix="/api/articles", tags=["articles"])
app.include_router(bookmarks.router, prefix="/api/bookmarks", tags=["bookmarks"])
app.include_router(interactions.router, prefix="/api/interactions", tags=["interactions"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

# LD client
import os
import ldclient
from ldclient.config import Config

@app.on_event("startup")
async def startup_event():
    # Start the background worker
    news_worker.start()
    # Initialize LaunchDarkly client
    sdk_key = os.getenv("LD_SDK_KEY")
    if sdk_key:
        config = Config(sdk_key)
        ld_client = ldclient.LDClient(config)
        app.state.ld_client = ld_client
    else:
        # If no SDK key, set to None (flags will fallback to default)
        app.state.ld_client = None

@app.on_event("shutdown")
async def shutdown_event():
    # Stop the background worker
    news_worker.stop()
    # Close LD client if exists
    if hasattr(app.state, 'ld_client') and app.state.ld_client:
        app.state.ld_client.close()

@app.get("/")
async def root():
    return {"message": "Welcome to the Trust-Aware Personalized AI News Intelligence System API"}

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers"""
    # Check if worker is running
    worker_status = "running" if news_worker.running else "stopped"

    # Check database connection (simplified)
    db_status = "unknown"
    try:
        # Try to ping the database
        await storage_service.users.count_documents({}, limit=1)
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "worker": worker_status,
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }