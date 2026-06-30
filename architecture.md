# Architecture.md

# NewsWise AI: Streamlit-Based AI News Intelligence Bot

## 1. Architecture Overview

NewsWise AI is designed as a lightweight, API-driven AI news intelligence system hosted on **Streamlit Community Cloud**. Streamlit Community Cloud is suitable for this Final Year Project (FYP) because it supports free deployment from GitHub repositories and provides a public `streamlit.app` URL for sharing the prototype. citeturn5search55turn5search50

Because Streamlit Community Cloud has limited free resources, the system avoids running heavy local AI models inside the Streamlit container. Instead, the architecture uses Streamlit mainly as the **UI orchestration layer**, while heavy AI tasks such as summarization, sentiment analysis, and optional speech processing are delegated to lightweight algorithms or external APIs. Streamlit Community Cloud apps may hit memory limits, so large transformer models should be avoided for the hosted prototype. citeturn5search43turn6search65

---

## 2. Key Architectural Principle

The upgraded architecture follows this principle:

> **Streamlit handles interface, state, caching, and orchestration. External APIs and lightweight modules handle AI processing. Persistent user data is stored outside local runtime files.**

This is important because Streamlit reruns the entire script from top to bottom whenever users interact with widgets or when the code changes. Therefore, expensive operations must be protected using caching and session state. citeturn6search65turn6search59

---

## 3. Improved High-Level Architecture

```text
+------------------------------------------------------+
|                    User Browser                      |
|------------------------------------------------------|
| - Opens Streamlit app URL                            |
| - Interacts with dashboard, filters, chatbot          |
| - Selects interests and reads AI news summary         |
+---------------------------↓--------------------------+

+------------------------------------------------------+
|             Streamlit Community Cloud App            |
|------------------------------------------------------|
| UI Layer                                             |
| - Dashboard                                          |
| - Explore News                                       |
| - Trust Check                                        |
| - AI Assistant                                       |
| - Profile & Preferences                              |
|                                                      |
| State & Cache Layer                                  |
| - st.session_state for per-user session data          |
| - st.cache_data for fetched news and processed data   |
| - st.cache_resource for DB/API clients if needed      |
+---------------------------↓--------------------------+

+------------------------------------------------------+
|              Application Logic Layer                 |
|------------------------------------------------------|
| - News fetch orchestration                           |
| - Data normalization                                 |
| - Deduplication                                      |
| - Topic classification                               |
| - Sentiment analysis                                 |
| - Summarization                                      |
| - Trust score calculation                            |
| - Recommendation ranking                             |
+---------------------------↓--------------------------+

+-------------------------+    +-----------------------+
| External News Sources   |    | External AI Services  |
|-------------------------|    |-----------------------|
| - RSS feeds             |    | - LLM summarization   |
| - News API / GNews      |    | - Sentiment API       |
| - Trusted publishers    |    | - STT/TTS optional    |
+-------------------------+    +-----------------------+

+------------------------------------------------------+
|                 External Data Layer                  |
|------------------------------------------------------|
| - Supabase / Firebase / Google Sheets                |
| - User preferences                                   |
| - Saved articles                                     |
| - Feedback                                           |
| - Cached article metadata                            |
|                                                      |
| Local read-only files                                |
| - source_credibility.csv                             |
| - sample_news.csv                                    |
+------------------------------------------------------+
```

---

## 4. Streamlit Execution Model Risk and Solution

### 4.1 Problem

Streamlit reruns the script from top to bottom for every user interaction. This means that if news fetching, summarization, and trust scoring are placed directly in the main app flow, the app may become slow or freeze after every button click. citeturn6search65turn6search59

### 4.2 Solution

The architecture introduces three performance boundaries:

```text
1. st.session_state
   Used for per-user data such as selected interests, chatbot history,
   selected article, and current filter choices.

2. st.cache_data
   Used for repeatable data results such as fetched news, cleaned news,
   processed article summaries, sentiment results, and trust scores.

3. st.cache_resource
   Used for reusable global resources such as database clients,
   API clients, or lightweight ML pipelines.
```

`st.cache_data` is suitable for caching serializable data such as DataFrames, API query results, and transformed data, while `st.cache_resource` is suitable for global resources such as database connections or ML models. citeturn6search65turn6search60

---

## 5. Revised Data Flow

### 5.1 Old Flow

```text
Fetch News
 ↓
Deduplicate
 ↓
Categorize
 ↓
Summarize
 ↓
Sentiment Analysis
 ↓
Trust Score
 ↓
Recommendation
 ↓
Display
```

### 5.2 Improved Flow

```text
User opens app
 ↓
Load cached news if available
 ↓
If cache expired, fetch limited batch of latest news
 ↓
Normalize article data
 ↓
Deduplicate articles
 ↓
Process only top N articles in real time
 ↓
Use cached summaries/trust scores for older articles
 ↓
Rank based on user preferences
 ↓
Display dashboard
```

This prevents the app from calling multiple external APIs every time the user clicks a widget.

---

## 6. Runtime Processing Strategy

To avoid the API latency waterfall problem, the system should follow this rule:

> **Do not process 20–50 articles with AI APIs during one user interaction.**

Instead, use this runtime policy:

```text
Runtime Processing Limit:
- Fetch: 10–20 headlines/articles
- Full AI analysis: Top 3–5 articles only
- Remaining articles: display title, source, snippet, and basic trust score
- Cache duration: 15–60 minutes depending on API limit
```

For API calls, batching or controlled concurrent requests can be used. However, because Streamlit documentation warns that async objects are not officially supported for `st.cache_resource`, the safer FYP approach is synchronous API calls with caching, or small controlled thread-based batches. citeturn6search60turn6search65

---

## 7. Multi-User State Management

### 7.1 Problem

Streamlit apps can serve multiple users. If the app writes user data to local CSV files during runtime, users may overwrite each other’s preferences or saved articles.

### 7.2 Rule

> **Local CSV files must be read-only during runtime.**

### 7.3 Updated Data Storage Design

| Data Type | Storage Location | Purpose |
|---|---|---|
| Static source credibility data | Local `source_credibility.csv` | Read-only reference data |
| Sample demo articles | Local `sample_news.csv` | Fallback demo dataset |
| Current user interests | `st.session_state` | Temporary per-session data |
| Chatbot conversation | `st.session_state` | Per-user chat history |
| Saved articles | Supabase / Firebase / Google Sheets | Persistent storage |
| User feedback | Supabase / Firebase / Google Sheets | Persistent evaluation data |
| Cached news results | `st.cache_data` or external DB | Reduce repeated API calls |

This design prevents local file-write conflicts and supports cleaner multi-user behavior. Streamlit Session State is intended to persist data between reruns for each user session, while cached data can be shared across users depending on how it is used. citeturn6search61turn6search65

---

## 8. Updated Module Architecture

### 8.1 Folder Structure

```text
newswise-ai/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── pages/
│   ├── 1_Dashboard.py
│   ├── 2_Explore.py
│   ├── 3_Trust_Check.py
│   ├── 4_AI_Assistant.py
│   └── 5_Profile.py
│
├── modules/
│   ├── news_fetcher.py
│   ├── data_normalizer.py
│   ├── deduplicator.py
│   ├── summarizer.py
│   ├── sentiment.py
│   ├── trust_score.py
│   ├── recommender.py
│   ├── storage.py
│   └── utils.py
│
├── data/
│   ├── source_credibility.csv
│   └── sample_news.csv
│
└── assets/
    ├── logo.png
    └── screenshots/
```

---

## 9. Data Normalization Layer

RSS feeds and commercial news APIs return different payload formats. Therefore, `news_fetcher.py` should not pass raw API/RSS data directly to the rest of the system.

Instead, the system introduces a **Data Normalizer / Adapter**.

### 9.1 Unified Article Object

```text
Article
- article_id
- title
- source
- author
- published_at
- url
- image_url
- category
- snippet
- full_text_optional
- language
- country
```

### 9.2 Data Normalization Flow

```text
RSS Feed / News API / GNews API
 ↓
Raw payload
 ↓
data_normalizer.py
 ↓
Unified Article object
 ↓
Deduplication
 ↓
NLP analysis
 ↓
Recommendation engine
```

This makes the architecture cleaner, easier to test, and easier to migrate later to FastAPI or another backend framework.

---

## 10. Caching Strategy

### 10.1 What Should Be Cached?

```text
@st.cache_data
- Fetching RSS/API news
- Cleaning and normalizing news data
- Deduplication results
- Sentiment result
- Summary result
- Trust score result
- Recommendation ranking result

@st.cache_resource
- Supabase client
- API client
- Optional lightweight ML pipeline
```

### 10.2 Recommended Cache TTL

```text
News fetching: 15–30 minutes
Summaries: 1–6 hours
Sentiment results: 1–6 hours
Trust scores: 1–6 hours
Source credibility CSV: 24 hours
```

`st.cache_data` supports caching function outputs and can be configured with parameters such as TTL, while `st.cache_resource` can be used for resources such as database connections or model objects. citeturn6search65turn6search60

---

## 11. Trust Score Architecture

The trust score module is the core research component of NewsWise AI.

### 11.1 Trust Score Formula

```text
Trust Score =
30% Source Credibility
25% Cross-Source Verification
20% Metadata Completeness
15% Headline-Content Consistency
10% Sentiment Neutrality
```

### 11.2 Trust Level

```text
85–100 = High Trust
60–84  = Medium Trust
40–59  = Needs Verification
0–39   = High Risk
```

### 11.3 Lightweight Implementation Strategy

To keep the system suitable for free Streamlit hosting:

```text
Source Credibility:
- Read from local source_credibility.csv

Cross-Source Verification:
- Compare article title and keywords with other fetched articles
- Use TF-IDF + cosine similarity
- Limit comparison to current cached batch

Metadata Completeness:
- Check source, author, date, URL, and article snippet availability

Headline-Content Consistency:
- Compare headline keywords with article snippet/full text keywords

Sentiment Neutrality:
- Penalize extremely emotional or sensational tone
```

For the FYP version, the output should be described as **misinformation risk scoring** or **trustworthiness assessment**, not as perfect fake-news detection.

---

## 12. AI Processing Architecture

### 12.1 Summarization

Recommended approach:

```text
Primary:
- LLM API summarization using Streamlit secrets

Fallback:
- Extractive summarization using sentence ranking
```

Large transformer models should not be run locally on Streamlit Community Cloud because free resource limits can cause deployment failures or out-of-memory issues. citeturn5search43turn6search65

### 12.2 Sentiment Analysis

Recommended approach:

```text
Primary:
- Lightweight sentiment model or external API

Fallback:
- VADER sentiment analysis
```

### 12.3 Chatbot

The chatbot should not process the entire news database every time. It should answer based on:

```text
- Current cached news batch
- Selected article
- User preferences
- Top recommended articles
```

---

## 13. Optional Voice Architecture

If voice features are included, audio processing should not be handled locally inside the Streamlit container.

### 13.1 Recommended Voice Design

```text
User voice input
 ↓
Browser audio recording
 ↓
External STT API / browser speech recognition
 ↓
Text query
 ↓
AI chatbot response
 ↓
Optional external TTS API / browser speech synthesis
```

### 13.2 Voice Components

```text
Speech-to-Text:
- Browser Web Speech API, or
- External Whisper/Gemini/Groq/OpenAI-compatible STT API

Text-to-Speech:
- Browser speech synthesis, or
- External TTS API
```

For the FYP version, voice should be treated as an optional enhancement unless the project scope specifically requires multimodal interaction.

---

## 14. Deployment Architecture

```text
GitHub Repository
 ↓
Streamlit Community Cloud
 ↓
Select repository, branch, and app.py
 ↓
Add API keys in Streamlit secrets
 ↓
Deploy
 ↓
Public streamlit.app URL
```

Streamlit Community Cloud deploys apps directly from GitHub, allows selecting the repository, branch, and entry-point file, and supports storing environment variables or API keys through the app’s secrets settings. citeturn5search50turn5search55

---

## 15. Dependency Strategy

### 15.1 Recommended Lightweight `requirements.txt`

```text
streamlit
pandas
numpy
requests
feedparser
beautifulsoup4
scikit-learn
nltk
vaderSentiment
plotly
supabase
python-dotenv
```

### 15.2 Dependencies to Avoid for Free Hosting

```text
transformers
torch
tensorflow
sentence-transformers
```

These packages can increase deployment time, memory usage, and risk of exceeding free Streamlit resource limits. citeturn5search43turn6search65

---

## 16. Final Architecture Diagram for Report

```text
+================================================================+
|                        NewsWise AI                             |
|          AI News Intelligence Bot on Streamlit Cloud            |
+================================================================+

                         +----------------+
                         |      User      |
                         +-------+--------+
                                 |
                                 v
+----------------------------------------------------------------+
|                    Streamlit UI Layer                          |
|----------------------------------------------------------------|
| Dashboard | Explore | Trust Check | AI Assistant | Preferences |
+----------------------------------------------------------------+
                                 |
                                 v
+----------------------------------------------------------------+
|              State, Cache, and Control Layer                   |
|----------------------------------------------------------------|
| st.session_state                                               |
| - User interests                                               |
| - Selected article                                             |
| - Chat history                                                 |
| - UI filter state                                              |
|                                                                |
| st.cache_data                                                  |
| - News fetch results                                           |
| - Processed article data                                       |
| - Sentiment results                                            |
| - Summary results                                              |
| - Trust scores                                                 |
|                                                                |
| st.cache_resource                                              |
| - Database client                                              |
| - API client                                                   |
+----------------------------------------------------------------+
                                 |
                                 v
+----------------------------------------------------------------+
|                  Core Application Modules                      |
|----------------------------------------------------------------|
| news_fetcher.py                                                |
| data_normalizer.py                                             |
| deduplicator.py                                                |
| summarizer.py                                                  |
| sentiment.py                                                   |
| trust_score.py                                                 |
| recommender.py                                                 |
| storage.py                                                     |
+----------------------------------------------------------------+
            |                         |                         |
            v                         v                         v
+---------------------+   +----------------------+   +----------------------+
| External News APIs  |   | External AI APIs     |   | External Database    |
|---------------------|   |----------------------|   |----------------------|
| RSS feeds           |   | Summarization        |   | Supabase/Firebase    |
| News API            |   | Sentiment analysis   |   | User preferences     |
| GNews API           |   | Optional STT/TTS     |   | Saved articles       |
+---------------------+   +----------------------+   +----------------------+

                                 |
                                 v
+----------------------------------------------------------------+
|                 Local Read-Only Reference Data                 |
|----------------------------------------------------------------|
| source_credibility.csv                                         |
| sample_news.csv                                                |
+----------------------------------------------------------------+
```

---

## 17. Final Architecture Decision

The final architecture is:

> **A lightweight, API-driven, cache-aware Streamlit architecture for a personalized AI news intelligence bot under free-tier cloud resource constraints.**

This architecture is selected because it balances FYP feasibility, deployment cost, performance, and research value.

---

## 18. Required Architecture Improvements

### 18.1 Must-Have Improvements

```text
1. Add st.session_state into architecture.
2. Add st.cache_data and st.cache_resource into architecture.
3. Make local CSV files read-only.
4. Add external database for persistent user data.
5. Add data normalization layer.
6. Limit real-time AI processing to top 3–5 articles.
7. Use cached data for the rest.
8. Store API keys in Streamlit secrets.
```

### 18.2 Nice-to-Have Improvements

```text
1. Add Supabase for saved articles and user preferences.
2. Add thread-based batch processing for small API batches.
3. Add fallback mode using sample_news.csv.
4. Add optional voice processing through external APIs.
5. Add evaluation dashboard for FYP demonstration.
```

---

## 19. Recommended Architecture Title

Recommended report title:

> **A Resource-Constrained Cloud Architecture for a Personalized AI News Intelligence Bot Using Streamlit Community Cloud**

If voice is included:

> **A Resource-Constrained Cloud Architecture for a Text and Voice-Based AI News Intelligence Agent Using Streamlit Community Cloud**

More technical alternative:

> **Design of a Lightweight API-Driven News Summarization, Sentiment Analysis, and Trust-Scoring System under Streamlit Serverless Constraints**

---

## 20. Final Recommendation

For the FYP implementation, the recommended final system stack is:

```text
Frontend/UI:
- Streamlit Community Cloud

State:
- st.session_state

Caching:
- st.cache_data
- st.cache_resource

News Source:
- RSS feeds
- Optional News API / GNews

AI Processing:
- External LLM API
- Lightweight fallback methods

Trust Score:
- Rule-based scoring
- Lightweight TF-IDF similarity

Storage:
- Read-only CSV for static data
- Supabase for persistent user data

Voice:
- Optional external STT/TTS only
```

This upgraded architecture is defensible, realistic, and safer for a live Streamlit demonstration.
