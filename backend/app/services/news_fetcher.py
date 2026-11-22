import requests
import feedparser
import time
import re
import html
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
from app.core.config import settings
import logging

# Publisher names for feeds whose own feed title is untidy
# ("Malay Mail  -  Malaysia", "News – The Sun Malaysia").
FEED_SOURCE_NAMES = {"malaymail.com": "Malay Mail", "thesun.my": "The Sun"}
# Feeds served from a cache that can be hours old; a changing query value
# (every 5 minutes) asks for an up-to-date copy.
CACHE_BUSTED_HOSTS = {"malaymail.com"}


def _feed_host(feed_url: str) -> str:
    try:
        return (urlparse(feed_url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""

logger = logging.getLogger(__name__)

_SECRET_PARAM = re.compile(r"((?:api[_-]?key|apikey|token|key|secret|password)=)[^&\s'\"]+", re.I)


def _redact(text) -> str:
    """Hide credential values in URLs before they reach the logs."""
    return _SECRET_PARAM.sub(lambda m: m.group(1) + "***", str(text))


def _safe_page_get(url: str, max_redirects: int = 3, **kwargs):
    """GET a publisher page only if it (and every redirect) is on the public
    internet, so a feed link cannot make the server reach private addresses."""
    from app.services.image_cache import is_public_http_url
    for _ in range(max_redirects + 1):
        if not is_public_http_url(url):
            return None
        response = requests.get(url, allow_redirects=False, **kwargs)
        location = response.headers.get("Location") if hasattr(response, "headers") and response.headers else None
        if response.status_code in (301, 302, 303, 307, 308) and location:
            url = urljoin(url, location)
            continue
        return response
    return None


def _repair_mojibake(value: str) -> str:
    """Repair common UTF-8-as-Windows-1252 corruption from RSS feeds."""
    if not value or not re.search(r"[ÃÂâ€™â€œâ€â€“â€”â€¦ðŸ]", value):
        return value
    try:
        repaired = value.encode("cp1252").decode("utf-8")
        return repaired if repaired != value else value
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def _strip_html(raw_html: Optional[str]) -> str:
    """Convert publisher HTML fragments into clean display text.

    RSS descriptions commonly contain entities such as ``&nbsp;`` and
    numeric entities. Decode them after removing tags, then normalize all
    whitespace so entities never reach the UI or database.
    """
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(raw_html))
    text = html.unescape(text)
    text = _repair_mojibake(text)
    text = re.sub(r"[\s\u00a0\u2007\u202f]+", " ", text).strip()
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
                    logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries + 1}): {_redact(e)}. Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Request failed after {max_retries + 1} attempts: {_redact(e)}")
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
                    "title": _strip_html(article.get("title")),
                    "author": article.get("author"),
                    "source": article.get("source", {}).get("name"),
                    "url": article.get("url"),
                    "published_at": article.get("publishedAt"),
                    "description": _strip_html(article.get("description")),
                    "content": _strip_html(article.get("content")),
                    "urlToImage": article.get("urlToImage")
                })
            return articles
        except requests.RequestException:
            # Already logged in helper
            return []
        except Exception as e:
            logger.error(f"Error fetching from NewsAPI: {_redact(e)}")
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
                    "title": _strip_html(article.get("title")),
                    "author": article.get("author"),
                    "source": article.get("source", {}).get("name"),
                    "url": article.get("url"),
                    "published_at": article.get("publishedAt"),
                    "description": _strip_html(article.get("description")),
                    "content": _strip_html(article.get("content")),
                    "image": article.get("image")
                })
            return articles
        except Exception as e:
            # Already logged in helper for request errors, but catch any other exceptions
            logger.error(f"Error fetching from GNews: {_redact(e)}")
            return []

    def fetch_from_rss(self, feed_url: str, known_urls: Optional[set] = None) -> List[Dict]:
        try:
            host = _feed_host(feed_url)
            params = {"t": int(time.time() // 300)} if host in CACHE_BUSTED_HOSTS else None
            response = requests.get(
                feed_url,
                params=params,
                timeout=8,
                headers={"User-Agent": "Mozilla/5.0 (compatible; CandorNewsBot/1.0)"}
            )
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            source_name = FEED_SOURCE_NAMES.get(host) or feed.feed.get("title", "Unknown")
            articles = []
            for entry in feed.entries:
                content = entry.get("content", [{}])[0].get("value") if entry.get("content") else None
                raw_description = entry.get("description") or entry.get("summary")
                image_url = self._extract_rss_image(entry, content, raw_description)
                link = entry.get("link")
                if not image_url and link:
                    # Avoid opening every article page during refresh. RSS
                    # media/enclosure images are already extracted above.
                    image_url = None
                articles.append({
                    "title": _strip_html(entry.get("title")),
                    "author": entry.get("author", None),
                    "source": source_name,
                    "url": link,
                    "published_at": entry.get("published"),
                    "description": _strip_html(raw_description),
                    "content": _strip_html(content),
                    "image": self._normalize_image_url(image_url, link)
                })

            # Many RSS feeds omit media fields even though the article page
            # exposes an Open Graph image. Resolve those images concurrently
            # so one slow publisher does not block the entire feed refresh.
            known_urls = known_urls or set()
            missing_images = [article for article in articles
                              if not article.get("image") and article.get("url") and article["url"] not in known_urls]
            with ThreadPoolExecutor(max_workers=min(8, max(1, len(missing_images)))) as executor:
                futures = {
                    executor.submit(self._fetch_og_image, article["url"]): article
                    for article in missing_images
                }
                for future in as_completed(futures):
                    article = futures[future]
                    try:
                        article["image"] = self._normalize_image_url(future.result(), article.get("url"))
                    except Exception as exc:
                        logger.debug(f"Could not resolve fallback image for {article.get('url')}: {exc}")

            return articles
        except Exception as e:
            logger.error(f"Error fetching from RSS feed {feed_url}: {e}")
            return []

    @staticmethod
    def _normalize_image_url(image_url: Optional[str], article_url: Optional[str]) -> Optional[str]:
        """Return an absolute, browser-safe image URL."""
        if not image_url:
            return None
        value = html.unescape(str(image_url)).strip()
        if value.startswith("//"):
            value = "https:" + value
        elif article_url:
            value = urljoin(article_url, value)
        parsed = urlparse(value)
        return value if parsed.scheme in {"http", "https"} and parsed.netloc else None

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
            response = _safe_page_get(
                article_url,
                timeout=6,
                headers={"User-Agent": "Mozilla/5.0 (compatible; CandorNewsBot/1.0)"}
            )
            if response is None or response.status_code != 200:
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

    def fetch_all_sources(self, selected_platforms: Optional[List[str]] = None, known_urls: Optional[set] = None) -> List[Dict]:
        """Fetch news from configured sources, optionally restricted to selected platforms."""
        all_articles = []
        selected = {name.strip().lower() for name in (selected_platforms or []) if name and name.strip()}

        selected_feeds = []
        feed_aliases = {
            "bernama": ("bernama",),
            "new straits times": ("nst",),
            "free malaysia today": ("freemalaysiatoday",),
            "malay mail": ("malaymail",),
            "the sun": ("thesun",),
        }
        if selected:
            for feed_url in settings.RSS_FEEDS.split(","):
                feed_url = feed_url.strip()
                if feed_url and any(
                    alias in feed_url.lower()
                    for platform in selected
                    for alias in feed_aliases.get(platform, (platform.replace(" ", ""),))
                ):
                    selected_feeds.append(feed_url)
        else:
            selected_feeds = [feed.strip() for feed in settings.RSS_FEEDS.split(",") if feed.strip()]

        def fetch_feed(feed_url):
            return feed_url, self.fetch_from_rss(feed_url, known_urls)

        with ThreadPoolExecutor(max_workers=min(6, max(1, len(selected_feeds)))) as executor:
            futures = [executor.submit(fetch_feed, feed_url) for feed_url in selected_feeds]
            for future in as_completed(futures):
                feed_url, rss_articles = future.result()
                all_articles.extend(rss_articles)
                logger.info(f"Fetched {len(rss_articles)} articles from RSS feed: {feed_url}")

        if not selected:
            return all_articles

        filtered = [
            article for article in all_articles
            if any(name in (article.get("source") or "").lower() for name in selected)
        ]
        logger.info(f"Filtered refresh to platforms {sorted(selected)}: {len(filtered)} article(s)")
        return filtered