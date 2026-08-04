    # Product Requirements Document (PRD)

# Trust-Aware Personalized AI News Intelligence System

**Version:** 2.0 — Production Ready Implementation  
**Product Type:** Web Application  
**Recommended Stack:** React, FastAPI, MongoDB  
**Scope:** Production-Ready MVP with Enhanced Features  
**Prepared By:** Chong Jun Cheng  
**Date:** 2026-07-07

---

## 1. Product Overview

# Trust-Aware Personalized AI News Intelligence System (FYP)

## Core Value
Web-based news aggregator utilizing NLP, XAI, and recommender systems to help users discover, understand, and critically evaluate news.

## Key Features
* **Enhanced Aggregation:** NewsAPI.org, GNews.io, and RSS feeds with intelligent source selection
* **NLP Pipeline:** Topic classification, extractive summarization, and sentiment analysis
* **Personalization:** Tailored content recommendations based on user preferences, interaction history, and keyword matching
* **Explainable Trustworthiness Score:** A misinformation risk indicator with detailed component breakdown (source reputation, cross-verification, semantic similarity, headline consistency, metadata completeness)

## FYP Suitability
Combines web development, data collection, database design, NLP, recommender systems, and explainable AI into a single cohesive production-ready system.

---

## 2. Problem Statement

Users today receive news from many platforms, including news websites, mobile applications, social media, newsletters, and search engines. This creates information overload. Many users do not have enough time to read full articles from multiple sources, compare reports, or judge the reliability of every news item.

Existing news aggregators usually provide headlines and category filtering, but many do not offer a complete combination of personalization, summarization, sentiment analysis, and transparent trust indicators. As a result, users may face these problems:

- They spend too much time browsing irrelevant news.
- They miss articles that match their interests.
- They find it difficult to understand long articles quickly.
- They may not know whether an article is emotionally biased or neutral.
- They may not know whether an article is reported by trusted sources.
- They may not understand why a news item is recommended.

This project addresses these issues by creating a personalized and trust-aware news intelligence system with production-ready enhancements.

---

## 3. Product Goals and Objectives

### 3.1 Product Goal
To help users consume personalized news efficiently while understanding the article summary, sentiment, recommendation reason, and trustworthiness level with detailed explanations.

### 3.2 Project Objectives
The project aims to collect news from APIs and RSS feeds, store article metadata, remove duplicate articles, classify articles into topics, generate extractive summaries, analyze sentiment, calculate explainable trustworthiness scores with source verification, recommend articles based on user interests and behavior, and evaluate the system using technical metrics and user feedback.

---

## 4. Target Users

### 4.1 Primary Users
The primary users are university students, working adults, readers interested in AI, technology, business, finance, and Malaysia news, and users who want quick daily summaries with basic reliability indicators.

### 4.2 Secondary Users
Secondary users may include researchers, journalism students, media monitoring users, and people interested in misinformation awareness.

---

## 5. Product Scope

### 5.1 In Scope for MVP
The MVP includes user registration and login, topic preference selection, news collection from APIs and RSS feeds, article metadata storage, duplicate removal, topic classification, extractive summarization, sentiment analysis, explainable trustworthiness scoring with source verification, personalized recommendation feed with behavior-based scoring, article detail page, bookmarking, basic interaction tracking, source credibility configuration, health monitoring endpoint, Docker support, and comprehensive unit testing.

### 5.2 Out of Scope for MVP
The MVP excludes mobile application, Telegram bot, full collaborative filtering, claim-level fact checking, real-time social media monitoring, automatic truth verification, advanced multilingual support, push notifications, paid subscriptions, and browser extension.

---

## 6. Key Features and Requirements

### 6.1 User Registration and Authentication
Users can create an account, log in, and manage news preferences. Authentication is required so the system can store user interests, bookmarks, and reading history.

**Functional requirements:**
- User can register using name, email, and password.
- User can log in securely.
- Passwords must be hashed before storage.
- User preferences are linked to the user account.

**Acceptance criteria:**
- A new user can register successfully.
- A registered user can log in.
- User preferences are saved and retrieved correctly.

### 6.2 Topic Preference Selection
During onboarding, users select preferred topics. These topics are used as the first signal for personalized recommendations.

**Supported topics:** Technology, Business, Politics, Sports, Health, AI, Local Malaysia News, Entertainment, and Finance.

**Functional requirements:**
- User can select one or more topics.
- User can update preferences later.
- Selected topics influence feed ranking.

### 6.3 News Collection Module
The system collects news from selected APIs and RSS feeds. Sources include NewsAPI.org, GNews.io, and configured RSS feeds.

Each article should store title, author if available, published date, source name, URL, description, content excerpt, topic/category, and image URL if available.

**Functional requirements:**
- The system fetches news on a scheduled basis.
- New articles are stored in MongoDB.
- New articles are initially saved with `processing_status = pending`.
- Exact duplicate URLs are not saved repeatedly.
- Missing fields are handled gracefully.
- Implements `fetch_all_sources()` method to combine API and RSS sources.

### 6.4 Deduplication Module
The system removes duplicate or near-duplicate articles to avoid showing the same story many times.

**Methods:** Exact URL matching, title similarity checking, and TF-IDF cosine similarity for near duplicates.

**Acceptance criteria:**
- Articles with identical URLs are removed.
- Articles with highly similar titles are grouped or filtered.

### 6.5 Topic Classification Module
Each article receives one main topic. The system may use API-provided categories, keyword rules, or TF-IDF-based classification. If the topic cannot be detected, the article is labeled as `General`.

**Acceptance criteria:**
- Each stored article has a topic.
- At least 80% of manually sampled articles should have reasonable topic labels.

### 6.6 Summarization Module
The system generates short summaries for news articles. For MVP, **extractive summarization** is recommended because it selects important sentences from the source text and reduces hallucination risk.

**Functional requirements:**
- Generate a 2 to 4 sentence summary.
- Use the article description as fallback if content is insufficient.
- Display summaries only after processing is completed.
- Avoid inventing facts not found in the original text.

### 6.7 Sentiment Analysis Module
The system analyzes the tone of each article using the title, description, and content excerpt.

**Sentiment labels:** Positive, Neutral, Negative.

**Functional requirements:**
- Assign a sentiment label to each article.
- Store a confidence score if available.
- Display sentiment clearly on the feed and detail page.

### 6.8 Trustworthiness Scoring Module
The trustworthiness module estimates whether an article may require further verification. The system avoids absolute labels such as “fake” or “real”. Instead, it uses risk-aware labels: **High Trust**, **Medium Trust**, **Low Trust**, and **Needs Verification**.

**Trust score formula:**
```
Trust Score =
30% Source Reputation
+ 25% Cross-Source Verification
+ 20% Semantic Similarity
+ 15% Headline-Content Consistency
+ 10% Metadata Completeness
```

**Score interpretation:**
```
80–100: High Trust
60–79: Medium Trust
40–59: Low Trust
0–39: Needs Verification
```

**Source reputation** is based on a manually maintained credibility list. **Cross-source verification** checks whether similar stories appear in other trusted sources. **Semantic similarity** compares the article with related trusted reports using TF-IDF cosine similarity or sentence embeddings. **Headline-content consistency** checks whether the headline matches the article description or content excerpt. **Metadata completeness** checks whether author, date, source, URL, and description are available.

**Enhanced Features:**
- **Similar Article Discovery:** Uses `find_similar_articles()` method to discover relevant articles from database by topic and timeframe (last 7 days)
- **Improved Cross-Source Verification:** Uses actual similar articles when available for verification scoring
- **Semantic Similarity Enhancement:** Uses TF-IDF with cosine similarity when scikit-learn is available, falls back to Jaccard similarity otherwise
- **Proper Fallback:** Uses `cold_start_fallback()` when no similar articles are found, dynamically recalibrating weights to use available local indicators

**Acceptance criteria:**
- Every completed article receives a numeric trust score and label.
- Users can view detailed explanations behind the score showing each component's contribution.
- The system communicates that the score is a risk indicator, not a final truth judgment.

### 6.9 Personalized Recommendation Module
The recommendation engine ranks articles based on user preferences, article freshness, interaction history, keyword similarity, source preference, and trust score. It should only recommend articles where `processing_status = completed`.

**Recommendation signals:** Selected topics, article topic, freshness, clicks, bookmarks, keyword similarity, source preference, and trust score.

**Enhanced Recommendation Formula:**
```
Recommendation Score =
35% Topic Preference Match
+ 20% Article Freshness
+ 15% User Interaction Similarity
+ 15% Trust Score
+ 10% Keyword Similarity
+ 5% Source Preference
```

**Enhanced Component Implementations:**
- **User Interaction Similarity:** Analyzes user's interaction history to find topical and source preferences
- **Keyword Similarity:** Uses Jaccard similarity between article keywords and user interest keywords
- **Source Preference:** Checks if article source matches user's preferred sources

The system should also provide a short explanation, such as:
```
Recommended because this article matches your AI interest, was published recently, and has a high trust score.
```

### 6.10 Bookmarking and Reading History
Users can save articles for later. The system also records basic interactions such as clicks and bookmarks. These interactions help improve future recommendations.

---

## 7. User Stories

### 1. Registration & Preference Selection
**As a** new user,  
**I want to** register an account on the news website and select my preferred topics,  
**So that** the system can instantly start personalizing my experience.

### 2. Personalized News Website Feed
**As a** user,  
**I want to** browse a personalized news feed on the website,  
**So that** I can easily find relevant and interesting articles in one place.

### 3. Personalized Alerts
**As a** user,  
**I want to** receive personalized notifications for breaking or highly relevant news,  
**So that** I can stay updated on my favorite topics without constantly checking the website.

### 4. AI-Powered Article Summaries
**As a** user,  
**I want to** read short, AI-generated summaries of articles,  
**So that** I can understand the core story quickly without reading the entire text immediately.

### 5. Content Analytics (Sentiment & Trust)
**As a** user,  
**I want to** view the automated sentiment analysis and trustworthiness indicators for each article,  
**So that** I can critically evaluate the tone, potential bias, and reliability risk of the news.

---

## 8. User Flow

### 8.1 New User Flow
```
User visits website
↓
User registers account
↓
User selects preferred topics
↓
System saves preferences
↓
System reads completed pre-processed articles from MongoDB
↓
System generates personalized feed
↓
User opens article detail page
↓
User views summary, sentiment, trust score with detailed explanation, and recommendation reason
↓
User bookmarks article or opens original source
```

### 8.2 Returning User Flow
```
User logs in
↓
System retrieves preferences and history
↓
System ranks latest completed articles from MongoDB using enhanced recommendation algorithm
↓
User reads or bookmarks articles
↓
System updates interaction history
```

**Important note:** News collection, deduplication, summarization, sentiment analysis, and trust scoring do not run during login. These heavy processes run separately in the background ingestion pipeline.

---

## 9. Data Model

### 9.1 Users Collection
Stores user ID, name, email, password hash, preferred topics, created date, and updated date.

### 9.2 Articles Collection
Stores article ID, title, author, source, URL, published date, description, content excerpt, image URL, topic, summary, keywords, sentiment result, sentiment score, trust score, trust explanation, trust components breakdown, `processing_status` (`pending`, `completed`, or `failed`), and `processed_at` timestamp. The frontend should only display articles with `processing_status = completed` unless an admin/debug view is used.

### 9.3 User Interactions Collection
Stores interaction ID, user ID, article ID, action type such as click or bookmark, and timestamp.

### 9.4 Source Credibility Collection
Stores source ID, source name, domain, credibility score, category, notes, and last updated date.

---

## 10. API Requirements

### Authentication APIs
```
POST /api/auth/register
POST /api/auth/login
```

### User APIs
```
GET /api/users/me
PUT /api/users/preferences
```

### Article APIs
```
GET /api/articles/feed
GET /api/articles/{article_id}
GET /api/articles/search?query=AI&topic=Technology
GET /api/articles/trending
```
The article feed, detail, search, and trending endpoints should filter out incomplete articles by default using `processing_status = completed`.

### Bookmark APIs
```
POST /api/bookmarks/{article_id}
DELETE /api/bookmarks/{article_id}
GET /api/bookmarks
```

### Interaction and Admin APIs
```
POST /api/interactions/click
POST /api/admin/fetch-news
POST /api/admin/reprocess-articles
```

### Health Check API
```
GET /api/health
```

---

## 11. System Architecture

The system uses a split-pipeline architecture. News ingestion and NLP processing run in the background, while the user-facing FastAPI application only reads pre-processed data from MongoDB. This prevents slow NLP tasks from blocking user requests and improves feed response time.

```
[Ingestion Pipeline / Background Worker]
APIs / RSS Feeds
↓
News Collection Service (Enhanced: NewsAPI + GNews + RSS)
↓
Deduplication Service
↓
NLP Pipeline
├── Topic Classification
├── Summarization
├── Sentiment Analysis
├── Trust Scoring (Enhanced: with similar article discovery)
└── Keyword Extraction
↓
MongoDB Articles Collection
(processing_status: completed / failed)
```

```
[User-Facing App / FastAPI]
User Login or Feed Request
↓
Authentication and Preference Lookup
↓
Read Pre-Processed Articles from MongoDB
(filter: processing_status = completed)
↓
Enhanced Recommendation Ranking
(Behavior-based: interaction history, keyword similarity, source preference)
↓
Fast Personalized Feed Delivery
↓
React Frontend
```

This architecture separates heavy background processing from real-time user interactions. The ingestion pipeline can run on a schedule or background worker, while the frontend receives only completed and ready-to-display articles.

---

## 12. Recommended Technology Stack

- **Frontend:** React
- **Backend:** FastAPI
- **Database:** MongoDB Atlas for development
- **News Sources:** NewsAPI.org, GNews.io, and RSS feeds using `feedparser`
- **Background Jobs:** APScheduler background tasks for scheduled ingestion
- **NLP:** scikit-learn, spaCy, and DistilBERT
- **Summarization:** TextRank using NetworkX using scikit-learn
- **Sentiment Analysis:** VADER for rule-based baseline and DistilBERT-based sentiment classification via Hugging Face Transformers
- **Recommendation:** TF-IDF vector similarity using scikit-learn, with Jaccard similarity for keyword matching
- **Trust Scoring:** Enhanced with similar article discovery, TF-IDF cosine similarity, and detailed component breakdown
- **Deployment:** Vercel for React frontend, Render for FastAPI backend, and MongoDB Atlas for managed MongoDB hosting
- **Monitoring:** Health:** Docker health checks and `/health` endpoint

---

## 13. Main UI Pages

The web application should include login and register pages, a topic selection page, a personalized feed page, an article detail page, a bookmarks page, and a profile/preferences page.

The personalized feed should show article cards with title, source, date, topic, summary, sentiment label, trust score badge with tooltip showing detailed explanation, and bookmark button. The article detail page should show summary, sentiment, trust score explanation with component breakdown, recommendation reason with personalization details, and original source link.

---

## 14. Non-Functional Requirements

### Performance
- News feed should load within 3 seconds under normal test conditions.
- Background news collection and NLP processing should not block user actions.

### Reliability
- The system should handle API failures gracefully.
- RSS feeds should act as backup sources if APIs are unavailable.
- Missing article fields should not crash the system.
- Failed NLP jobs should mark articles as `processing_status = failed`.

### Security
- Passwords must be hashed.
- API keys must not be exposed in frontend code.
- User input must be validated.
- Authentication tokens should be handled securely.

### Maintainability
- Backend modules should be separated by responsibility.
- Ingestion and NLP processing should be separate from user-facing API route logic.
- Trust score weights should be configurable.
- Source credibility data should be editable.
- Enhanced trust scoring components should be modular and testable.

### Ethical and Legal Considerations
- Store metadata, summaries, and short excerpts only.
- Link users to the original article source.
- Avoid claiming perfect fake news detection.
- Explain that trust scores are advisory risk indicators with component-level transparency.

---

## 15. Evaluation Plan

### 15.1 Summarization Evaluation
Use ROUGE-1, ROUGE-2, ROUGE-L, and human ratings for readability and factual accuracy. Human evaluators can compare generated summaries with original article descriptions.

### 15.2 Sentiment Analysis Evaluation
Manually label a sample of articles as positive, neutral, or negative. Evaluate the system using accuracy, precision, recall, F1-score, and confusion matrix.

### 15.3 Recommendation Evaluation
Evaluate recommendation quality using Precision@K, click-through rate, bookmark rate, and user satisfaction survey. Users can rate whether top recommended articles match their interests.

### 15.4 Trust Score Evaluation
Evaluate trust scoring by comparing system labels with manual review. The evaluation should also test cold-start cases where no related article cluster exists and verify component-level explanations are accurate.

### 15.5 User Acceptance Test
Conduct testing with approximately 20 to 30 users. Ask whether the personalized feed is relevant, summaries are useful, sentiment labels are understandable, trust explanations are clear and informative, and whether they would use the system.

---

## 16. Risks and Mitigation

| Risk | Mitigation |
|------|------------|
| API request limits | Use RSS feeds as backup; implement caching |
| AI hallucination | Use extractive summarization |
| Overclaiming fake news detection | Use trust score and risk labels with explanations instead of fake/real labels |
| Cold-start trust score penalty | Recalibrate formula when no related cluster exists using available local indicators |
| Copyright issues | Store metadata, short excerpts, and source links only |
| Scope too large | Complete MVP first before adding chatbot or mobile app |
| Missing or failed article processing | Use `processing_status` and filter incomplete articles from frontend |
| Recommendation bias | Include trending or diverse articles section in future version |

---

## 17. Development Timeline

### Phase 1: Planning and Research (Days 1 – 14)
* **Duration:** 14 days
* **Key Tasks:** * Finalize the Project Requirement Document (PRD).
    * Confirm News APIs, RSS feeds, and data sources.
    * Design the system architecture (FastAPI + APScheduler decoupled worker setup).
    * Prepare the comprehensive evaluation plan for NLP and Trust metrics.

### Phase 2: Backend Foundation & Database Setup (Days 15 – 28)
* **Duration:** 14 days
* **Key Tasks:**
    * Set up the FastAPI environment and configure MongoDB Atlas cloud connection.
    * Implement user authentication (JWT/OAuth2) and secure endpoints.
    * Design and build core database models for users, articles, and logs.

### Phase 3: News Collection and Preprocessing Pipeline (Days 29 – 42)
* **Duration:** 14 days
* **Key Tasks:**
    * Integrate chosen News APIs / RSS feeds into a background script.
    * Configure APScheduler to automate collection intervals.
    * Normalize incoming article text fields and implement a deduplication hash check.
    * Store newly ingested articles with a `pending` status.
    * Implement enhanced news fetching with API source selection.

### Phase 4: Core NLP Analytics Pipeline (Days 43 – 63)
* **Duration:** 21 days
* **Key Tasks:**
    * Implement rapid topic classification (scikit-learn baseline).
    * Deploy TextRank using NetworkX for graph-based extractive summarization.
    * Integrate Hugging Face (DistilBERT) for deep contextual sentiment analysis.
    * Extract keywords via spaCy for personalization indexing; update article status to `processed`.

### Phase 5: Explainable Trust Scoring & Recommendation Engine (Days 64 – 77)
* **Duration:** 14 days
* **Key Tasks:**
    * Build a source credibility matrix and mathematical trust-risk scoring formula.
    * Implement user interaction logging (clicks/bookmarks) to feed a weighted recommendation algorithm.
    * Filter out already completed/read articles and generate personalized recommendations with behavior-based scoring.
    * Set up fallback rules for new users (cold-start mitigation).
    * Implement enhanced trust scoring with similar article discovery and component explanations.

### Phase 6: Frontend Interface Development (Days 71 – 91)
* **Duration:** 21 days *(Note: Overlaps slightly with backend algorithms for seamless integration)*
* **Key Tasks:**
    * Set up the React template and connect deployment pipelines to Vercel.
    * Build UI views: Registration, login, onboarding topic selection, and personalized feed.
    * Develop the article detail view highlighting summaries, sentiment charts, trust indicators with detailed explanations, and personalized recommendation reasons.
    * Build user bookmarks, notification profile settings, and history tracking.

### Phase 7: Testing and Evaluation (Days 85 – 91)
* **Duration:** 7 days *(Overlaps with final frontend refinements)*
* **Key Tasks:**
    * Conduct end-to-end system functional testing (FastAPI to React via Vercel/Render).
    * Evaluate NLP pipeline accuracy and recommendation relevance.
    * Run User Acceptance Testing (UAT) to catch workflow anomalies.
    * Execute unit tests for frontend components and backend models.

### Phase 8: Final Documentation and Presentation (Days 92 – 98)
* **Duration:** 7 days
* **Key Tasks:**
    * Compile the final thesis/FYP report including system architecture and evaluation results.
    * Draft final sequence, dataflow, and entity-relationship diagrams.
    * Prepare presentation slides, rehearse the system demonstration, and record backup project footage.

---

## 18. MVP Release Criteria
The MVP is complete when users can register, log in, select preferred topics, view a personalized feed of completed articles, read article summaries, see sentiment labels, review trust scores with detailed explanations and component breakdown, bookmark articles, and access basic evaluation results. The system must also collect and store articles, filter duplicates, classify topics, process news through the background NLP pipeline with enhanced trust scoring, and prevent incomplete articles from appearing in the normal user feed.

---

## 19. Future Enhancements
Future versions may include Telegram bot integration, web chatbot integration, multilingual news support, collaborative filtering, bot queries, push notifications, multilingual news support, collaborative filtering, claim-level verification, timeline view for developing stories, compare sources feature, viewpoint diversity recommendation, browser extension, and mobile application.

---

## 20. Final MVP Statement
The final MVP is a web-based personalized news intelligence system that allows users to select news interests, view recommended pre-processed articles, read extractive summaries, analyze sentiment, and review an explainable trustworthiness score based on source credibility, metadata quality, cross-source similarity, headline consistency, and enhanced personalization through behavioral analysis.

This version is realistic for a Final Year Project because it is achievable within a student timeline while still demonstrating meaningful technical depth. It is stronger than a basic news aggregator because it combines background news ingestion, personalization, NLP, recommendation logic, and explainable misinformation risk assessment with transparency in one integrated system.