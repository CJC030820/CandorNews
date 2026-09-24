# News Intelligence System v2.0 — Complete Implementation Guide

![Status](https://img.shields.io/badge/Status-Production%20Ready-green)
![Version](https://img.shields.io/badge/Version-2.0-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## 🎯 Overview

A **production-ready web application** that aggregates personalized news with explainable AI trust scores, sentiment analysis, and intelligent recommendations. Combines NLP, recommendation algorithms, and trust scoring to help users understand and evaluate news critically.

**Live Stack:**
- **Frontend:** React 18 (Vite/CRA) + Nginx
- **Backend:** FastAPI + MongoDB + APScheduler
- **NLP:** scikit-learn + spaCy + Transformers (DistilBERT)
- **Recommendation:** TF-IDF cosine similarity + behavior-based ranking
- **Deployment:** Docker Compose / Kubernetes / Cloud Run

---

## ✨ Core Features

### 👤 User Management
- ✅ Registration with email verification-ready
- ✅ JWT-based authentication (Bearer tokens)
- ✅ Topic preference selection (9 categories)
- ✅ Profile management and account deletion

### 📰 News Processing
- ✅ Multi-source aggregation (NewsAPI, GNews, RSS feeds)
- ✅ Automatic deduplication
- ✅ Background NLP pipeline with status tracking
- ✅ Topic classification (ML-powered)
- ✅ Extractive summarization (TextRank)
- ✅ Sentiment analysis (VADER + DistilBERT)

### 🤖 Trust Scoring & Transparency
```
Trust Score = 40% Source Reputation
           + 35% Cross-Source Verification
           + 12% Headline-Content Consistency
           + 13% Metadata Completeness

80-100: High Trust  | 60-79: Medium Trust | 40-59: Low Trust | 0-39: Needs Verification
```

### 📊 Personalized Recommendations
```
Recommendation = 35% Topic Match
              + 20% Freshness
              + 15% User Interaction Similarity
              + 15% Trust Score
              + 10% Keyword Similarity
              + 5%  Source Preference
```

### 🔖 User Interactions
- ✅ Bookmarking articles
- ✅ Reading history tracking
- ✅ Click-through analytics
- ✅ Email digest notifications

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- Docker & Docker Compose
- Python 3.10+ (for local development)
- 4GB RAM minimum

### Local Development

```bash
# 1. Clone and navigate
git clone https://github.com/yourorg/newscollectbot.git
cd newscollectbot

# 2. Setup environment
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys (optional for local testing)

# 3. Start all services
docker compose up --build

# Wait for all services to be healthy...
# ✓ Backend ready at http://localhost:8080
# ✓ Frontend ready at http://localhost:3000
# ✓ MongoDB ready at localhost:27017

# 4. Run integration tests (optional)
python test_system_integration.py

# 5. Access the application
open http://localhost:3000  # or http://127.0.0.1:3000
```

### Test Account (Local)
- **Email:** test@example.com
- **Password:** password123
- Or create a new account

---

## 📁 Project Structure

```
newscollectbot/
├── backend/                          # FastAPI application
│   ├── app/
│   │   ├── api/v1/endpoints/        # API routes
│   │   │   ├── auth.py              # Authentication (register, login)
│   │   │   ├── articles.py          # Feed, search, trending
│   │   │   ├── bookmarks.py         # Bookmark management
│   │   │   ├── users.py             # User preferences
│   │   │   └── admin.py             # Admin operations
│   │   ├── services/
│   │   │   ├── storage.py           # MongoDB operations
│   │   │   ├── news_fetcher.py      # NewsAPI + RSS aggregation
│   │   │   ├── nlp_pipeline.py      # NLP processing
│   │   │   ├── recommender.py       # Recommendation engine
│   │   │   ├── trust_scorer.py      # Trust scoring
│   │   │   └── email_service.py     # Email notifications
│   │   ├── models/                  # Pydantic V2 models
│   │   ├── core/
│   │   │   ├── config.py            # Settings & env vars
│   │   │   └── security.py          # JWT + password hashing
│   │   ├── main.py                  # FastAPI app + startup hooks
│   │   └── worker.py                # Background job scheduler
│   ├── requirements.txt              # Python dependencies
│   ├── Dockerfile                   # Multi-stage build
│   └── .env.example                 # Configuration template
│
├── frontend/                         # React application
│   ├── src/
│   │   ├── pages/                   # Route components
│   │   │   ├── LoginPage.js
│   │   │   ├── RegisterPage.js
│   │   │   ├── TopicSelectionPage.js
│   │   │   ├── FeedPage.js
│   │   │   ├── ArticleDetailPage.js
│   │   │   └── BookmarksPage.js
│   │   ├── components/              # Reusable components
│   │   │   ├── ArticleCard.js
│   │   │   ├── NavBar.js
│   │   │   └── DarkModeToggle.js
│   │   ├── context/
│   │   │   ├── AuthContext.js       # Auth state management
│   │   │   └── BookmarkContext.js   # Bookmark state
│   │   ├── services/                # API clients
│   │   ├── App.js                   # Main app component
│   │   └── index.js                 # Entry point
│   ├── package.json
│   ├── Dockerfile                   # Multi-stage build
│   └── nginx.conf                   # Production server config
│
├── docker-compose.yml               # Orchestration with health checks
├── test_system_integration.py       # End-to-end test suite
├── quick-start.sh                   # Automated setup script
├── DEPLOYMENT_GUIDE.md              # Production deployment
├── SYSTEM_UPDATE_v2.0.md            # Latest updates
└── README.md                         # This file
```

---

## 🔌 API Endpoints

### Authentication
```
POST   /api/auth/register          # Create account
POST   /api/auth/login             # Login (returns JWT)
GET    /api/auth/me                # Current user (requires Bearer token)
```

### Articles
```
GET    /api/articles/feed          # Personalized feed (limit=20)
GET    /api/articles/{id}          # Article detail
GET    /api/articles?query=...     # Search articles
GET    /api/articles/trending      # Trending articles
```

### User Settings
```
GET    /api/users/me               # User profile
PUT    /api/users/preferences      # Update topic preferences
PUT    /api/users/profile          # Update name
DELETE /api/users/me               # Delete account
```

### Bookmarks
```
GET    /api/bookmarks              # Get bookmarked articles
POST   /api/bookmarks/{id}         # Bookmark article
DELETE /api/bookmarks/{id}         # Remove bookmark
```

### Health & Admin
```
GET    /api/health                 # System health check
POST   /api/admin/fetch-news       # Trigger news refresh (admin)
```

**Full API docs:** http://localhost:8080/docs (interactive Swagger UI)

---

## 🛠 Configuration

### Environment Variables (backend/.env)

```bash
# ===== CRITICAL FOR PRODUCTION =====
SECRET_KEY=<generate-with-openssl-rand-hex-32>
MONGODB_URL=mongodb://mongodb:27017
ALLOWED_ORIGINS=http://localhost:3000,http://localhost

# ===== News APIs (get free keys) =====
NEWSAPI_KEY=<from-newsapi.org>
GNEWS_API_KEY=<from-gnews.io>
RSS_FEEDS=<comma-separated-URLs>

# ===== Email (optional) =====
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=<app-password>

# ===== NLP Configuration =====
WORKER_INTERVAL_MINUTES=30
TRUST_WEIGHT_SOURCE_REPUTATION=0.40
TRUST_WEIGHT_CROSS_SOURCE=0.35
```

### Frontend Environment (frontend/.env)

```bash
REACT_APP_API_URL=http://localhost:8080
```

---

## 📊 System Architecture

### Split-Pipeline Design (Scalable)

```
[Background Processing]
─────────────────────────
Raw News (APIs + RSS)
    ↓
Deduplication Service
    ↓
NLP Pipeline:
  • Topic Classification (scikit-learn)
  • Summarization (TextRank)
  • Sentiment Analysis (DistilBERT)
  • Trust Scoring (Source + Cross-Verify)
    ↓
MongoDB (processing_status: completed)

[User-Facing API]
──────────────────
Request: GET /api/articles/feed?limit=20
    ↓
1. Auth (verify JWT)
2. Get User Preferences
3. Fetch completed articles
4. Rank with Recommendation Algorithm
5. Return top 20
    ↓
Response: [article, article, ...] ~< 500ms
```

**Benefits:**
- Background jobs don't block user requests
- Feed response time: ~300-500ms
- Batch processing efficiency
- Graceful error handling for failed articles

---

## 🧪 Testing

### Integration Test Suite
```bash
# Comprehensive end-to-end testing
python test_system_integration.py

# Tests:
# ✓ Backend health check
# ✓ User registration
# ✓ User login with JWT
# ✓ Topic preferences
# ✓ Article feed
# ✓ Article search
# ✓ Bookmarks
# ✓ Frontend accessibility
```

### Manual Testing Checklist
- [ ] Register new account
- [ ] Select topics
- [ ] View personalized feed
- [ ] Read article details
- [ ] Check sentiment & trust score
- [ ] Bookmark articles
- [ ] View bookmarks
- [ ] Dark mode toggle
- [ ] Logout

---

## 🚀 Deployment

### Quick Deployment Options

**Docker Compose (Single Server)**
```bash
docker compose -f docker-compose.yml up -d
```
See `docker-compose.yml` for health checks and service ordering.

**Production Checklist**
- [ ] Update `SECRET_KEY` in `.env`
- [ ] Configure real MongoDB Atlas
- [ ] Set `ALLOWED_ORIGINS` to your domain
- [ ] Enable HTTPS/TLS
- [ ] Set up monitoring & alerts
- [ ] Configure automated backups

See `DEPLOYMENT_GUIDE.md` for detailed instructions on:
- AWS ECS/Fargate
- Google Cloud Run
- Kubernetes
- DigitalOcean
- Heroku

---

## 🔐 Security Practices

✅ **Implemented:**
- Password hashing with bcrypt 4.3.0
- JWT tokens (Bearer scheme, no query params)
- Authorization header validation
- CORS with specific origin whitelist
- Environment variable secrets (not hardcoded)
- SQL injection protection (using MongoDB)
- XSS protection (React auto-escaping)
- CSRF protection (SameSite cookies)

⚠️ **For Production:**
- Enforce HTTPS only
- Use managed secrets (AWS Secrets Manager, etc.)
- Enable rate limiting
- Set up WAF (Web Application Firewall)
- Enable audit logging
- Regular dependency updates
- Security scanning (OWASP, SNYK)

---

## 📈 Performance Optimizations

### Backend
- Multi-stage Docker build (~350MB final image)
- MongoDB indexes on frequently queried fields
- JWT token caching
- Connection pooling
- Async/await for I/O operations

### Frontend
- Code splitting with React.lazy()
- CSS-in-JS tree-shaking
- Image lazy loading
- Service worker for offline support (PWA-ready)
- Production build minification

### Database
- Compound indexes on `topic` + `processing_status`
- TTL indexes for temporary data
- Connection pooling with motor
- Read replicas for scaling

---

## 🆘 Troubleshooting

### Backend issues
```bash
# View logs
docker compose logs backend

# Check health
curl http://localhost:8080/api/health

# Verify MongoDB connection
docker compose exec backend python -c "from app.services.storage import storage_service; print('DB OK')"
```

### Frontend issues
```bash
# Check console for errors
docker compose logs frontend

# Verify API connectivity
curl -H "Authorization: Bearer <token>" http://localhost:8080/api/auth/me
```

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `bcrypt: module has no attribute '__about__'` | Version mismatch | Update `requirements.txt` to bcrypt 4.3.0 |
| `CORS error` | Origin not whitelisted | Add to `ALLOWED_ORIGINS` in `.env` |
| `MongoDB connection refused` | Service not started | Wait for MongoDB healthcheck |
| `JWT decode error` | Token expired | Re-login to get fresh token |
| `No articles in feed` | Worker not running | Check `docker compose logs backend` for worker init |

---

## 📚 Documentation

- `SYSTEM_UPDATE_v2.0.md` — Latest features and fixes
- `DEPLOYMENT_GUIDE.md` — Production deployment strategies
- `AI_News_Intelligence_PRD.md` — Product requirements document
- `backend/app/main.py` — API documentation (Swagger UI)
- Backend API docs: `http://localhost:8080/docs`

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests: `python test_system_integration.py`
5. Commit: `git commit -am 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Create a Pull Request

---

## 📝 License

This project is licensed under the MIT License — see `LICENSE` file for details.

---

## 📞 Support

- 📧 Email: support@example.com
- 💬 Issues: GitHub Issues
- 📖 Docs: See `/docs` folder and inline comments
- 🐛 Bug Report: Use GitHub Issues with reproduction steps

---

## ✅ Updated June 2026 — v2.0

- ✅ Fixed bcrypt/passlib compatibility (4.3.0)
- ✅ Removed exposed credentials from .env
- ✅ Added full NLP pipeline dependencies
- ✅ Improved Docker orchestration with health checks
- ✅ Fixed auth to use Bearer token scheme (no query params)
- ✅ Updated Frontend to use environment-based API URL
- ✅ Comprehensive deployment guide
- ✅ Integration test suite
- ✅ Production-ready configuration

**Next Phase:** User acceptance testing, performance optimization, mobile app (out of scope for MVP)

---

**Ready to get started?** Run `docker compose up --build` and visit http://localhost:3000! 🚀
