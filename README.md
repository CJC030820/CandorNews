# Trust-Aware Personalized AI News Intelligence System

This is the implementation of the Trust-Aware Personalized AI News Intelligence System as described in the PRD.

## Project Structure

- `backend/`: FastAPI backend application
- `frontend/`: React frontend application

## Backend

The backend is built with FastAPI and uses MongoDB for data storage.

### Key Components

- Authentication (register, login, JWT)
- User preferences management
- News ingestion pipeline (fetching, deduplication, NLP processing)
- Trust scoring system
- Recommendation engine
- Bookmarking and interaction tracking
- Feature flags (LaunchDarkly)

### Running the Backend

1. Install dependencies:
   ```
   cd backend
   pip install -r requirements.txt
   ```

2. Set up environment variables (create a `.env` file based on `.env.example`):
   ```
   LD_SDK_KEY=your_launchdarkly_sdk_key_here
   NEWSAPI_KEY=your_newsapi_key_here
   GNEWS_API_KEY=your_gnews_api_key_here
   RSS_FEEDS=http://www.thestar.com.my/rss/main.xml,https://www.bernama.com/en/rss/news_rss.xml,https://www.malaymail.com/rss/all/
   MONGODB_URL=mongodb://localhost:27017
   DATABASE_NAME=news_intelligence
   SECRET_KEY=your-secret-key-here
   ```

3. Start the application:
   ```
   uvicorn app.main:app --reload
   ```

### Environment Variables

- `LD_SDK_KEY`: LaunchDarkly SDK key (server-side)
- `NEWSAPI_KEY`: NewsAPI key for fetching news from NewsAPI.org
- `GNEWS_API_KEY`: GNews API key for fetching news from GNews.io
- `RSS_FEEDS`: Comma-separated list of RSS feed URLs (defaults to Malaysia news sources)
- `MONGODB_URL`: MongoDB connection string
- `DATABASE_NAME`: Name of the MongoDB database
- `SECRET_KEY`: Secret key for JWT token signing

## Frontend

The frontend is built with React and React Router.

### Key Pages

- Login/Register
- Topic Selection
- Personalized Feed
- Article Detail
- Bookmarks
- Profile

### Running the Frontend

1. Install dependencies:
   ```
   cd frontend
   npm install
   ```

2. Set up environment variables (create a `.env` file):
   ```
   REACT_APP_LD_CLIENT_SIDE_ID=your_launchdarkly_client_side_id_here
   ```

3. Start the development server:
   ```
   npm start
   ```

## Docker Deployment

The system can be easily deployed using Docker Compose:

1. Copy `.env.example` to `.env` in the backend directory and fill in the values
2. Create a `.env` file in the frontend directory with `REACT_APP_LD_CLIENT_SIDE_ID`
3. Run:
   ```
   docker-compose up --build
   ```

The services will be available at:
- Backend API: http://localhost:8000
- Frontend: http://localhost
- MongoDB: localhost:27017 (exposed for debugging)

### Health Check

A health check endpoint is available at:
- http://localhost:8000/health

## Testing

### Backend Tests

Run the unit tests with pytest:
```
cd backend
pytest tests/
```

### Frontend Tests

Run the frontend tests with Jest:
```
cd frontend
npm test
```

## Features Implemented

- ✅ User registration and authentication with JWT
- ✅ Topic preference selection and management
- ✅ News aggregation from multiple sources (NewsAPI, GNews, RSS feeds)
- ✅ Duplicate article detection
- ✅ Topic classification
- ✅ Extractive summarization
- ✅ Sentiment analysis
- ✅ Explainable trustworthiness scoring (based on source reputation, cross-verification, semantic similarity, headline consistency, and metadata completeness)
- ✅ Personalized recommendation engine
- ✅ Bookmarking and interaction tracking (clicks, bookmarks, views)
- ✅ Feature flags using LaunchDarkly for gradual rollouts
- ✅ Docker support for easy deployment
- ✅ Health check endpoint for monitoring
- ✅ Comprehensive unit tests

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

MIT