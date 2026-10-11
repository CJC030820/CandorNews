"""
Frontend integration configuration for smooth page transitions.
Defines API response timeout and animation synchronization settings.
"""

# Page transition timing (must match frontend PageTransition.css)
PAGE_TRANSITION_DURATION_MS = 300  # milliseconds

# Maximum acceptable API response time before frontend considers page transition delayed
MAX_RESPONSE_TIME_MS = 2000  # milliseconds (2 seconds)

# API timeout warning threshold
API_TIMEOUT_THRESHOLD_MS = 1500  # milliseconds

# Response headers that support frontend transitions
TRANSITION_RESPONSE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY"
}

# Endpoints that should prioritize speed (minimal processing)
TRANSITION_PRIORITY_ENDPOINTS = [
    "/api/articles/feed",
    "/api/auth/me",
    "/api/users/profile",
    "/api/bookmarks",
    "/api/history"
]
