import requests
import feedparser
import time
import re
from typing import List, Dict, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def _strip_html(raw_html: Optional[str]) -> str:
    """Remove HTML tags/entities from RSS description/content fields so the
    frontend doesn't render raw markup."""
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = re.sub(r"\s+", " ", text).strip()
    return text

class NewsFetcherService:
    def __init__(self):
        self.newsapi_key = settings.NEWSAPI_KEY
        self.gnews_api_key = settings.GNEWS_API_KEY

    def _make_request_with_retry(self, url: str, params: dict, max_retries: int = 3, backoff_factor: float = 0.5) -> requests.Response:
        """Make a GET request with retry logic.

        Args:
            url: The URL to request
            params: Query parameters
            max_retries: Maximum number of retry attempts
            backoff_factor: Backoff factor for exponential delay between retries

        Returns:
            requests.Response object

        Raises:
            requests.RequestException: If all retries fail
        """
        for attempt in range(max_retries + 1):
            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                if attempt < max_retries:
                    wait_time = backoff_factor * (2 ** attempt)
                    logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Request failed after {max_retries + 1} attempts: {e}")
                    raise

    def fetch_from_newsapi(self, query: str = "", category: str = "", language: str = "en", country: str = "my") -> List[Dict]:
        if not self.newsapi_key:
            logger.warning("NewsAPI key not configured")
            return []
        url = "https://newsapi.org/v2/top-headlines"
        params = {
            "apiKey": self.newsapi_key,
            "q": query,
            "category": category,
            "language": language,
            "country": country,
            "pageSize": 100
        }
        try:
            response = self._make_request_with_retry(url, params)
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
        except requests.RequestException:
            # Already logged in helper
            return []
        except Exception as e:
            logger.error(f"Error fetching from NewsAPI: {e}")
            return []

    def fetch_from_gnews(self, query: str = "", category: str = "", language: str = "en", country: str = "my") -> List[Dict]:
        if not self.gnews_api_key:
            logger.warning("GNews API key not configured")
            return []
        url = "https://gnews.io/api/v4/top-headlines"
        params = {
            "token": self.gnews_api_key,
            "q": query,
            "category": category,
            "lang": language,
            "country": country,
            "max": 100
        }
        try:
            response = self._make_request_with_retry(url, params)
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
            # Already logged in helper for request errors, but catch any other exceptions
            logger.error(f"Error fetching from GNews: {e}")
            return []

    def fetch_from_rss(self, feed_url: str) -> List[Dict]:
        try:
            feed = feedparser.parse(feed_url)
            articles = []
            for entry in feed.entries:
                content = entry.get("content", [{}])[0].get("value") if entry.get("content") else None
                raw_description = entry.get("description") or entry.get("summary")
                image_url = self._extract_rss_image(entry, content, raw_description)
                link = entry.get("link")
                if not image_url and link:
                    # Some feeds (e.g. Bernama) carry no image data at all in
                    # the RSS entry itself. Fall back to scraping the
                    # article page's Open Graph / Twitter image meta tag.
                    image_url = self._fetch_og_image(link)
                articles.append({
                    "title": _strip_html(entry.get("title")),
                    "author": entry.get("author", None),
                    "source": feed.feed.get("title", "Unknown"),
                    "url": link,
                    "published_at": entry.get("published"),
                    "description": _strip_html(raw_description),
                    "content": _strip_html(content),
                    "image": image_url
                })
            return articles
        except Exception as e:
            logger.error(f"Error fetching from RSS feed {feed_url}: {e}")
            return []

    def _extract_rss_image(self, entry: dict, content: Optional[str], raw_description: Optional[str]) -> Optional[str]:
        """Best-effort extraction of an article image from an RSS entry,
        checking (in order): media:content, media:thumbnail, enclosures,
        then falling back to the first <img> tag found in the raw HTML
        content/description/summary."""
        media_content = entry.get("media_content")
        if media_content:
            url = media_content[0].get("url")
            if url:
                return url

        media_thumbnail = entry.get("media_thumbnail")
        if media_thumbnail:
            url = media_thumbnail[0].get("url")
            if url:
                return url

        enclosures = entry.get("enclosures")
        if enclosures:
            for enc in enclosures:
                enc_type = enc.get("type", "")
                if enc_type.startswith("image") or not enc_type:
                    url = enc.get("href") or enc.get("url")
                    if url:
                        return url

        # Fall back to scanning raw HTML for the first <img src="...">
        for html_blob in (content, raw_description, entry.get("summary")):
            if html_blob:
                match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html_blob)
                if match:
                    return match.group(1)

        return None

    def _fetch_og_image(self, article_url: str) -> Optional[str]:
        """Fetch an article page and extract its Open Graph / Twitter card
        image URL. Used as a last-resort fallback for RSS feeds (e.g.
        Bernama) that don't include any image data in the feed itself.
        Fails silently (returns None) so a slow/broken page never blocks
        ingestion of the rest of the batch."""
        try:
            response = requests.get(
                article_url,
                timeout=6,
                headers={"User-Agent": "Mozilla/5.0 (compatible; CandorNewsBot/1.0)"}
            )
            if response.status_code != 200:
                return None
            html = response.text
            for pattern in (
                r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
                r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
            ):
                match = re.search(pattern, html)
                if match:
                    return match.group(1)
            return None
        except Exception as e:
            logger.debug(f"Could not fetch OG image for {article_url}: {e}")
            return None

    def fetch_all_sources(self) -> List[Dict]:
        """Fetch news from all configured sources (NewsAPI, GNews, RSS)"""
        all_articles = []

        # Fetch from NewsAPI
        newsapi_articles = self.fetch_from_newsapi()
        all_articles.extend(newsapi_articles)

        # Fetch from GNews
        gnews_articles = self.fetch_from_gnews()
        all_articles.extend(gnews_articles)

        # Fetch from RSS feeds
        rss_feeds = settings.RSS_FEEDS.split(",")
        for feed_url in rss_feeds:
            feed_url = feed_url.strip()
            if feed_url:
                rss_articles = self.fetch_from_rss(feed_url)
                all_articles.extend(rss_articles)
                logger.info(f"Fetched {len(rss_articles)} articles from RSS feed: {feed_url}")

        return all_articles