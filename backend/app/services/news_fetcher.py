import requests
import feedparser
from typing import List, Dict, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class NewsFetcherService:
    def __init__(self):
        self.newsapi_key = settings.NEWSAPI_KEY
        self.gnews_api_key = settings.GNEWS_API_KEY

    def fetch_from_newsapi(self, query: str = "", category: str = "", language: str = "en") -> List[Dict]:
        if not self.newsapi_key:
            logger.warning("NewsAPI key not configured")
            return []
        url = "https://newsapi.org/v2/top-headlines"
        params = {
            "apiKey": self.newsapi_key,
            "q": query,
            "category": category,
            "language": language,
            "pageSize": 100
        }
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            articles = []
            for article in data.get("articles", []):
                articles.append({
                    "title": article.get("title"),
                    "author": article.get("author"),
                    "source": article.get("source", {}).get("name"),
                    "url": article.get("url"),
                    "published_at": article.get("publishedAt"),
                    "description": article.get("description"),
                    "content": article.get("content"),
                    "urlToImage": article.get("urlToImage")
                })
            return articles
        except Exception as e:
            logger.error(f"Error fetching from NewsAPI: {e}")
            return []

    def fetch_from_gnews(self, query: str = "", category: str = "", language: str = "en") -> List[Dict]:
        if not self.gnews_api_key:
            logger.warning("GNews API key not configured")
            return []
        url = "https://gnews.io/api/v4/top-headlines"
        params = {
            "token": self.gnews_api_key,
            "q": query,
            "category": category,
            "lang": language,
            "max": 100
        }
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            articles = []
            for article in data.get("articles", []):
                articles.append({
                    "title": article.get("title"),
                    "author": article.get("author"),
                    "source": article.get("source", {}).get("name"),
                    "url": article.get("url"),
                    "published_at": article.get("publishedAt"),
                    "description": article.get("description"),
                    "content": article.get("content"),
                    "image": article.get("image")
                })
            return articles
        except Exception as e:
            logger.error(f"Error fetching from GNews: {e}")
            return []

    def fetch_from_rss(self, feed_url: str) -> List[Dict]:
        try:
            feed = feedparser.parse(feed_url)
            articles = []
            for entry in feed.entries:
                articles.append({
                    "title": entry.get("title"),
                    "author": entry.get("author", None),
                    "source": feed.feed.get("title", "Unknown"),
                    "url": entry.get("link"),
                    "published_at": entry.get("published"),
                    "description": entry.get("description"),
                    "content": entry.get("content", [{}])[0].get("value") if entry.get("content") else None
                })
            return articles
        except Exception as e:
            logger.error(f"Error fetching from RSS feed {feed_url}: {e}")
            return []

    def fetch_all_sources(self) -> List[Dict]:
        """Fetch news from all configured API sources"""
        all_articles = []

        # Fetch from NewsAPI
        newsapi_articles = self.fetch_from_newsapi()
        all_articles.extend(newsapi_articles)

        # Fetch from GNews
        gnews_articles = self.fetch_from_gnews()
        all_articles.extend(gnews_articles)

        return all_articles