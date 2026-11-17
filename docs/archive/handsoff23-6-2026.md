# Hands-off Summary for Feature Flag Implementation (LaunchDarkly)

## Date: 2026-06-23

## Overview
Implemented a feature flag system using LaunchDarkly to enable remote configuration and gradual rollouts of features in the NewsCollectBot application.

## Changes Made

### Backend (FastAPI)
1. **Dependencies**:
   - Added `ldclient-py` to `backend/requirements.txt`

2. **Initialization** (`backend/app/main.py`):
   - Imported `ldclient` and `Config`
   - Added startup event to initialize LD client using `LD_SDK_KEY` environment variable
   - Added shutdown event to close LD client properly
   - Stored LD client in `app.state.ld_client`
   - Added dependency function `get_ld_client()` to retrieve LD client from app state

3. **Utility Function** (`backend/app/utils/ld_utils.py`):
   - Created `get_flag(ld_client, context, flag_key, default_value)` function
   - Safely retrieves flag values, returning default if LD client is unavailable or errors occur

4. **API Endpoint** (`backend/app/api/v1/articles.py`):
   - Added import for `get_ld_client` and `get_flag`
   - Added `User` model import for current user dependency
   - Created `GET /articles/flags/{flag_key}` endpoint:
     - Takes current user from auth dependency
     - Creates LD context with user ID and email
     - Returns flag value for the specified flag key
     - Uses `get_flag` utility for safe retrieval

### Frontend (React)
1. **Dependencies**:
   - Added `ldclient-js` and `ldclient-react` to `frontend/package.json`

2. **Initialization** (`frontend/src/index.js`):
   - Imported `LDProvider` from `ldclient-react` and `LDClient` from `ldclient-js`
   - Initialized LD client using `REACT_APP_LD_CLIENT_SIDE_ID` environment variable
   - Wrapped `<App />` with `<LDProvider client={ldClient}>`

3. **Usage Example** (`frontend/src/pages\FeedPage.js`):
   - Imported `useLDFlag` from `ldclient-react`
   - Used hook: `const showNewFeature = useLDFlag('new_feature', false);`
   - Added conditional rendering to demonstrate flag consumption:
     ```jsx
     {showNewFeature && <p>New feature is enabled! This is a feature flag example.</p>}
     ```

## Environment Variables Required
### Backend
- `LD_SDK_KEY`: LaunchDarkly SDK key (server-side)

### Frontend
- `REACT_APP_LD_CLIENT_SIDE_ID`: LaunchDarkly client-side ID

## Example Usage
### Backend (in any route or service):
```python
from fastapi import Depends
from app.main import get_ld_client
from app.utils.ld_utils import get_flag

# In route handler:
async def some_route(current_user: User = Depends(get_current_user), ld_client = Depends(get_ld_client)):
    context = {
        "key": str(current_user.id),
        "email": current_user.email,
        # Add any other attributes for targeting
    }
    feature_enabled = get_flag(ld_client, context, "some-flag-key", False)
```

### Frontend (in any React component):
```javascript
import { useLDFlag } from "ldclient-react";

function MyComponent() {
  const isFeatureEnabled = useLDFlag("some-flag-key", false);
  
  return (
    <div>
      {isFeatureEnabled ? (
        <NewFeatureComponent />
      ) : (
        <OldFeatureComponent />
      )}
    </div>
  );
}
```

## Notes
- All LaunchDarkly calls are wrapped with error handling to fall back to default values
- The flag endpoint in backend requires authentication to provide user context for targeting
- Frontend usage follows standard LaunchDarkly React SDK patterns
- Remember to add actual flag keys in LaunchDarkly dashboard for the flags used in code

## Next Steps
1. Configure feature flags in LaunchDarkly dashboard
2. Set environment variables in deployment environments
3. Begin using flags for feature toggles, A/B testing, or gradual rollouts
4. Consider adding more context attributes for advanced targeting (user roles, preferences, etc.)