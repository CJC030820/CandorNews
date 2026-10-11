"""
Middleware for smooth frontend page transitions.
Ensures proper response timing, caching, and headers.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
import logging

logger = logging.getLogger(__name__)


class TransitionHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds headers to support smooth page transitions on the frontend.
    Ensures consistent response timing and proper cache control.
    """
    
    async def dispatch(self, request, call_next) -> Response:
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        
        # Disable caching for API endpoints to ensure fresh data on page transitions
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        # Add performance timing header (useful for debugging slow transitions)
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
