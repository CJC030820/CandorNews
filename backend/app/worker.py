from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

from app.services.news_fetcher import NewsFetcherService
from app.services.deduplicator import DeduplicatorService
from app.services.topic_classifier import TopicClassifierService
from app.services.summarizer import SummarizerService
from app.services.sentiment_analyzer import SentimentAnalyzerService
from app.services.trust_scorer import TrustScorerService
from app.services import image_cache
from app.services.keyword_extractor import KeywordExtractorService
from app.services.storage import storage_service
from app.core.config import settings
import asyncio
from typing import Dict, List

logger = logging.getLogger(__name__)

try:
    from langdetect import detect, DetectorFactory
    # Make detection deterministic (langdetect is otherwise seeded randomly,
    # which can flip borderline results between runs).
    DetectorFactory.seed = 0
    _LANGDETECT_AVAILABLE = True
except ImportError:
    _LANGDETECT_AVAILABLE = False
    logger.warning("langdetect not available; falling back to heuristic English filter only.")

# Common Malay/Indonesian function words. If a title/description is heavy
# with these but detection is unavailable or inconclusive, treat it as
# non-English. Kept intentionally short and high-signal to avoid false
# positives against English text.
_MALAY_STOPWORDS = {
    "yang", "dan", "untuk", "dengan", "ini", "itu", "pada", "dari", "ke",
    "akan", "adalah", "kata", "telah", "tidak", "juga", "sebagai", "kerana",
    "selepas", "sebelum", "antara", "mereka", "kami", "kita", "beliau",
    "dijangka", "berkata", "menteri", "kerajaan", "negara",
    "dakwa", "didakwa", "bunuh", "nenek", "keluar", "hari",
    "sertai", "parti"
}


def _looks_malay(text: str) -> bool:
    """Cheap heuristic: if enough recognizable Malay/Indonesian stopwords
    appear in the text, treat it as Malay even if langdetect disagrees."""
    words = re.findall(r"[a-zA-Z']+", text.lower())
    if not words:
        return False
    malay_hits = sum(1 for w in words if w in _MALAY_STOPWORDS)
    return malay_hits >= 2


def is_english_article(title: str, description: str = "", content: str = "") -> bool:
    """Return True if the article text looks like English, so non-English
    (mainly Bahasa Malaysia) articles from mixed-language RSS feeds like
    Free Malaysia Today get filtered out before ever being saved."""
    sample = " ".join(t for t in (title, description, content[:300] if content else "") if t).strip()
    if not sample:
        return True  # nothing to judge - don't block on missing text

    if _looks_malay(sample):
        return False

    if _LANGDETECT_AVAILABLE:
        try:
            return detect(sample) == "en"
        except Exception:
            # Detection failed (e.g. text too short/ambiguous) - fall back to
            # allowing it through rather than silently dropping articles.
            return True

    return True


def _parse_published_date(raw_value, fallback_now=True):
    """Normalize aware feed dates to naive UTC for MongoDB storage."""
    parsed = raw_value if isinstance(raw_value, datetime) else None
    if isinstance(raw_value, str):
        try:
            parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed = parsedate_to_datetime(raw_value)
            except (ValueError, TypeError):
                pass
    if parsed is None:
        return datetime.utcnow() if fallback_now else None
    return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed


class NewsWorker:
    def __init__(self):
        """Initialize the news worker with all required services."""
        self.scheduler = AsyncIOScheduler()
        self.news_fetcher = NewsFetcherService()
        self.deduplicator = DeduplicatorService()
        self.topic_classifier = TopicClassifierService()
        self.summarizer = SummarizerService()
        self.sentiment_analyzer = SentimentAnalyzerService()
        self.trust_scorer = TrustScorerService()
        self.keyword_extractor = KeywordExtractorService()
        self.running = False
        self.last_run_at = None
        self.last_run_stats = {}
        # Guards against overlapping fetch cycles (e.g. the background
        # worker's startup run racing with a manual "Refresh News" click, or
        # the scheduled email job's pre-send refresh firing at the same time
        # as the periodic interval run). Without this, two cycles could both
        # fetch the same upstream articles and race on the same URLs.
        self._fetch_lock = asyncio.Lock()

    async def process_article(self, raw_article: Dict) -> bool:
        """Process a single raw article through the pipeline. Returns True if
        it was newly saved, False if skipped (missing fields or already exists)."""
        url = raw_article.get("url")
        title = raw_article.get("title")
        source = raw_article.get("source") or "Unknown"

        try:
            parsed_url = urlparse(url or "")
        except ValueError:
            return False
        if not url or not title or parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
            return False

        try:
            # Skip articles we've already ingested (persistent dedup across runs)
            existing = await storage_service.get_article_by_url(url)
            if existing:
                return False

            description = raw_article.get("description") or ""
            content = raw_article.get("content") or ""

            # Filter out non-English articles (some feeds, e.g. Free
            # Malaysia Today, mix English and Bahasa Malaysia articles in
            # the same RSS feed).
            if not is_english_article(title, description, content):
                logger.info(f"Skipping non-English article: {title}")
                return False

            # Topic classification (up to 3 categories, ranked by relevance)
            topics = self.topic_classifier.classify_topics(title, description, content)
            primary_topic = topics[0]

            # Summarization
            summary = self.summarizer.summarize(content or description or title)

            # Sentiment analysis
            sentiment_result = self.sentiment_analyzer.analyze_article_sentiment(raw_article)

            # Extract keywords (used both for storage and cross-source
            # corroboration lookup below)
            keywords = self.keyword_extractor.extract_keywords(
                f"{title} {description} {content}", max_keywords=10
            )

            # Look for other recently-ingested articles (from other sources)
            # that are genuinely reporting the same story (checked via real
            # title similarity, not just a shared generic keyword - sharing
            # a word like "government" or "said" is not real corroboration).
            # If multiple independent outlets are reporting the same actual
            # event, that's real evidence it happened, and the trust score
            # should reflect that with a meaningfully higher score instead of
            # staying flat around the cold-start default.
            candidate_articles = await storage_service.find_articles_by_keywords(
                keywords, exclude_url=url
            )
            original_date = _parse_published_date(raw_article.get("published_at"), fallback_now=False)
            published_date = original_date or datetime.utcnow()
            score_input = {**raw_article, **sentiment_result,
                           "published_date": original_date}
            trust_result = await self.trust_scorer.calculate_trust_score(
                score_input, [a.dict() for a in candidate_articles])

            # Prepare article for storage
            article_data = {
                "title": title,
                "author": raw_article.get("author"),
                "source": source,
                "url": url,
                "published_date": published_date,
                "publication_date_inferred": original_date is None,
                "description": description or None,
                "content_excerpt": content[:500] if content else None,
                "image_url": raw_article.get("urlToImage") or raw_article.get("image"),
                "topic": primary_topic,
                "topics": topics,
                "summary": summary,
                "keywords": keywords,
                "sentiment": sentiment_result["sentiment"],
                "sentiment_score": sentiment_result["sentiment_score"],
                "tone_label": sentiment_result.get("tone_label"),
                "trust_score": trust_result["trust_score"],
                "trust_explanation": trust_result["trust_explanation"],
                "processing_status": "completed",
                "processed_at": datetime.utcnow()
            }

            article_data.update(trust_result)
            from app.models.article import ArticleCreate
            created = await storage_service.create_article(ArticleCreate(**article_data))
            if created is None:
                # Another concurrent fetch cycle already inserted this exact
                # URL between our existence check and this insert - treat it
                # as already-ingested rather than a new save.
                return False
            logger.info(f"Saved new article: {title}")
            return True

        except Exception as e:
            logger.error(f"Error processing article {url}: {e}", exc_info=True)
            return False

    async def fetch_and_process_news(self, selected_platforms=None) -> Dict:
        """Fetch news from sources and process them. Returns run stats.
        Serialized via a lock so overlapping calls (manual refresh vs.
        scheduled interval vs. pre-email refresh) never run concurrently and
        race on inserting the same articles."""
        if self._fetch_lock.locked():
            logger.info("A news fetch cycle is already running; waiting for it to finish instead of starting a duplicate run.")

        async with self._fetch_lock:
            return await self._fetch_and_process_news_locked(selected_platforms)

    async def _fetch_and_process_news_locked(self, selected_platforms=None) -> Dict:
        logger.info("Starting news fetch cycle")
        stats = {"fetched": 0, "unique": 0, "saved": 0, "started_at": datetime.utcnow().isoformat()}
        try:
            # NewsFetcherService uses blocking requests/feedparser calls, so
            # run it in a worker thread to avoid stalling the event loop.
            loop = asyncio.get_event_loop()
            # Articles already stored do not need their page re-opened to look
            # up an image; this keeps repeated requests to publishers low.
            known_urls = {a.url for a in await storage_service.get_latest_articles(limit=500)}
            all_articles = await loop.run_in_executor(
                None, self.news_fetcher.fetch_all_sources, selected_platforms, known_urls)
            stats["fetched"] = len(all_articles)
            logger.info(f"Total articles fetched: {len(all_articles)}")

            # Deduplicate within this batch
            unique_articles = self.deduplicator.remove_duplicates(all_articles)
            stats["unique"] = len(unique_articles)
            logger.info(f"After deduplication: {len(unique_articles)} articles")

            # Process each article (skips ones already stored from prior runs)
            saved_count = 0
            saved_images = []
            for article in unique_articles:
                saved = await self.process_article(article)
                if saved:
                    saved_count += 1
                    saved_images.append(article.get("image"))
            stats["saved"] = saved_count
            # Keep a local copy of new images while the publisher is reachable.
            stats["images_cached"] = await loop.run_in_executor(None, image_cache.download_many, saved_images)
            # Self-repair: retry recent articles whose image is still missing.
            recent = await storage_service.get_latest_articles(limit=500)
            missing = [a.image_url for a in recent if a.image_url and not image_cache.cached(a.image_url)]
            stats["images_backfilled"] = await loop.run_in_executor(
                None, image_cache.download_many, missing[:image_cache.BACKFILL_LIMIT])
            stats["rescored"] = await self.rescore_recent_articles()

            logger.info(f"News fetch cycle completed. {saved_count} new article(s) saved.")
        except Exception as e:
            logger.error(f"Error in fetch and process news: {e}", exc_info=True)
            stats["error"] = str(e)

        stats["finished_at"] = datetime.utcnow().isoformat()
        self.last_run_at = stats["finished_at"]
        self.last_run_stats = stats
        storage_service.bump_articles_version()      # image copies and run stats changed too
        return stats

    async def rescore_recent_articles(self):
        """Refresh the latest 500 records after each batch, including older v1 scores."""
        articles = await storage_service.get_latest_articles(limit=500)
        changed = 0
        for article in articles:
            candidates = await storage_service.find_articles_by_keywords(article.keywords, article.url)
            result = await self.trust_scorer.calculate_trust_score(article.dict(), [a.dict() for a in candidates])
            # Only write when the score or its evidence changed (the time stamp alone does not count).
            if any(getattr(article, k, None) != v for k, v in result.items() if k != "trust_scored_at"):
                await storage_service.update_article_fields(article.id, result)
                changed += 1
        self.last_rescore_changed = changed
        return len(articles)

    def start(self):
        """Start the background worker: runs once immediately, then on a
        recurring interval (WORKER_INTERVAL_MINUTES)."""
        if not self.running:
            self.scheduler.add_job(
                self.fetch_and_process_news,
                IntervalTrigger(minutes=settings.WORKER_INTERVAL_MINUTES),
                id='news_fetch_job',
                replace_existing=True,
                next_run_time=datetime.utcnow()  # kick off an immediate first run
            )
            self.scheduler.start()
            self.running = True
            logger.info(
                f"Background news worker started (fetching every {settings.WORKER_INTERVAL_MINUTES} minutes)."
            )

    def stop(self):
        """Stop the background worker"""
        if self.running:
            self.scheduler.shutdown(wait=False)
            self.running = False
            logger.info("Background worker stopped")


# Create a global instance of the worker for import in other modules
news_worker = NewsWorker()
