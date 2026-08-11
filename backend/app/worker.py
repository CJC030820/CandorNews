from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
from datetime import datetime
from email.utils import parsedate_to_datetime

from app.services.news_fetcher import NewsFetcherService
from app.services.deduplicator import DeduplicatorService
from app.services.topic_classifier import TopicClassifierService
from app.services.summarizer import SummarizerService
from app.services.sentiment_analyzer import SentimentAnalyzerService
from app.services.trust_scorer import TrustScorerService
from app.services.keyword_extractor import KeywordExtractorService
from app.services.storage import storage_service
from app.core.config import settings
import asyncio
from typing import Dict, List

logger = logging.getLogger(__name__)


def _parse_published_date(raw_value) -> datetime:
    """Best-effort parsing of the many date formats NewsAPI/GNews/RSS return.
    Falls back to "now" (UTC) so an unparseable date never blocks ingestion."""
    if not raw_value:
        return datetime.utcnow()
    if isinstance(raw_value, datetime):
        return raw_value
    if isinstance(raw_value, str):
        # ISO 8601 (NewsAPI/GNews), e.g. "2024-01-01T12:00:00Z"
        try:
            return datetime.fromisoformat(raw_value.replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, TypeError):
            pass
        # RFC 2822 (most RSS feeds), e.g. "Fri, 08 Aug 2026 12:00:00 +0000"
        try:
            return parsedate_to_datetime(raw_value).replace(tzinfo=None)
        except (ValueError, TypeError):
            pass
    return datetime.utcnow()


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

    async def process_article(self, raw_article: Dict) -> bool:
        """Process a single raw article through the pipeline. Returns True if
        it was newly saved, False if skipped (missing fields or already exists)."""
        url = raw_article.get("url")
        title = raw_article.get("title")
        source = raw_article.get("source") or "Unknown"

        if not url or not title:
            return False

        try:
            # Skip articles we've already ingested (persistent dedup across runs)
            existing = await storage_service.get_article_by_url(url)
            if existing:
                return False

            description = raw_article.get("description") or ""
            content = raw_article.get("content") or ""

            # Topic classification
            topic = self.topic_classifier.classify_topic(title, description, content)

            # Summarization
            summary = self.summarizer.summarize(content or description or title)

            # Sentiment analysis
            sentiment_result = self.sentiment_analyzer.analyze_article_sentiment(raw_article)

            # Calculate trust score (cold-start: no cross-source comparison yet)
            trust_result = await self.trust_scorer.cold_start_fallback(raw_article)

            # Extract keywords
            keywords = self.keyword_extractor.extract_keywords(
                f"{title} {description} {content}", max_keywords=10
            )

            # Prepare article for storage
            article_data = {
                "title": title,
                "author": raw_article.get("author"),
                "source": source,
                "url": url,
                "published_date": _parse_published_date(raw_article.get("published_at")),
                "description": description or None,
                "content_excerpt": content[:500] if content else None,
                "image_url": raw_article.get("urlToImage") or raw_article.get("image"),
                "topic": topic,
                "summary": summary,
                "keywords": keywords,
                "sentiment": sentiment_result["sentiment"],
                "sentiment_score": sentiment_result["sentiment_score"],
                "trust_score": trust_result["trust_score"],
                "trust_explanation": trust_result["trust_explanation"],
                "processing_status": "completed",
                "processed_at": datetime.utcnow()
            }

            from app.models.article import ArticleCreate
            await storage_service.create_article(ArticleCreate(**article_data))
            logger.info(f"Saved new article: {title}")
            return True

        except Exception as e:
            logger.error(f"Error processing article {url}: {e}", exc_info=True)
            return False

    async def fetch_and_process_news(self) -> Dict:
        """Fetch news from sources and process them. Returns run stats."""
        logger.info("Starting news fetch cycle")
        stats = {"fetched": 0, "unique": 0, "saved": 0, "started_at": datetime.utcnow().isoformat()}
        try:
            # NewsFetcherService uses blocking requests/feedparser calls, so
            # run it in a worker thread to avoid stalling the event loop.
            loop = asyncio.get_event_loop()
            all_articles = await loop.run_in_executor(None, self.news_fetcher.fetch_all_sources)
            stats["fetched"] = len(all_articles)
            logger.info(f"Total articles fetched: {len(all_articles)}")

            # Deduplicate within this batch
            unique_articles = self.deduplicator.remove_duplicates(all_articles)
            stats["unique"] = len(unique_articles)
            logger.info(f"After deduplication: {len(unique_articles)} articles")

            # Process each article (skips ones already stored from prior runs)
            saved_count = 0
            for article in unique_articles:
                saved = await self.process_article(article)
                if saved:
                    saved_count += 1
            stats["saved"] = saved_count

            logger.info(f"News fetch cycle completed. {saved_count} new article(s) saved.")
        except Exception as e:
            logger.error(f"Error in fetch and process news: {e}", exc_info=True)
            stats["error"] = str(e)

        stats["finished_at"] = datetime.utcnow().isoformat()
        self.last_run_at = stats["finished_at"]
        self.last_run_stats = stats
        return stats

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
