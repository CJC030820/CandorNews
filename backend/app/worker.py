from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
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
import os
from typing import Dict, List

logger = logging.getLogger(__name__)

class NewsWorker:
    def __init__(self):
        """Initialize the news worker with all required services."""
        self.scheduler = BackgroundScheduler()
        self.news_fetcher = NewsFetcherService()
        self.deduplicator = DeduplicatorService()
        self.topic_classifier = TopicClassifierService()
        self.summarizer = SummarizerService()
        self.sentiment_analyzer = SentimentAnalyzerService()
        self.trust_scorer = TrustScorerService()
        self.keyword_extractor = KeywordExtractorService()
        self.running = False

    async def process_article(self, raw_article: Dict):
        """Process a single raw article through the pipeline"""
        try:
            # Extract basic information
            title = raw_article.get("title", "")
            description = raw_article.get("description", "")
            content = raw_article.get("content", "")

            # Topic classification
            topic = self.topic_classifier.classify(title, description, content)

            # Summarization
            summary = self.summarizer.summarize(content or description or title)

            # Sentiment analysis
            sentiment_result = self.sentiment_analyzer.analyze(title, description, content)

            # Calculate trust score (we'll need similar articles for cross-source, but for now use cold-start)
            trust_result = self.trust_scorer.cold_start_fallback(raw_article)

            # Extract keywords
            keywords = self.keyword_extractor.extract_keywords(
                f"{title} {description} {content}", max_keywords=10
            )

            # Prepare article for storage
            article_data = {
                "title": raw_article.get("title"),
                "author": raw_article.get("author"),
                "source": raw_article.get("source"),
                "url": raw_article.get("url"),
                "published_date": raw_article.get("published_at"),
                "description": raw_article.get("description"),
                "content_excerpt": raw_article.get("content", "")[:500],  # Limit excerpt
                "image_url": raw_article.get("urlToImage") or raw_article.get("image"),
                "topic": topic,
                "summary": summary,
                "keywords": keywords,  # Extract keywords using our new service
                "sentiment": sentiment_result["sentiment"],
                "sentiment_score": sentiment_result["sentiment_score"],
                "trust_score": trust_result["trust_score"],
                "trust_explanation": trust_result["trust_explanation"],
                "processing_status": "completed",
                "processed_at": None  # Will be set by storage service
            }

            # Save article
            await storage_service.create_article(article_data)
            logger.info(f"Processed and saved article: {raw_article.get('title')}")

        except Exception as e:
            logger.error(f"Error processing article {raw_article.get('url', 'unknown')}: {e}")

    async def fetch_and_process_news(self):
        """Fetch news from sources and process them"""
        logger.info("Starting news fetch cycle")
        try:
            # Fetch from API sources (NewsAPI, GNews)
            api_articles = self.news_fetcher.fetch_all_sources()
            logger.info(f"Fetched {len(api_articles)} articles from API sources")

            # Fetch from RSS feeds as backup/additional sources
            rss_feeds = [
                "http://www.thestar.com.my/rss/main.xml",
                "https://www.bernama.com/en/rss/news_rss.xml",
                "https://www.malaymail.com/rss/all/"
            ]

            rss_articles = []
            for feed_url in rss_feeds:
                articles = self.news_fetcher.fetch_from_rss(feed_url)
                rss_articles.extend(articles)
                logger.info(f"Fetched {len(articles)} articles from {feed_url}")

            # Combine all articles
            all_articles = api_articles + rss_articles
            logger.info(f"Total articles fetched: {len(all_articles)}")

            # Deduplicate
            unique_articles = self.deduplicator.remove_duplicates(all_articles)
            logger.info(f"After deduplication: {len(unique_articles)} articles")

            # Process each article
            for article in unique_articles:
                await self.process_article(article)

            logger.info("News fetch cycle completed")
        except Exception as e:
            logger.error(f"Error in fetch and process news: {e}")

    def start(self):
        """Start the background worker"""
        if not self.running:
            # Run every 30 minutes
            self.scheduler.add_job(
                self.fetch_and_process_news,
                IntervalTrigger(minutes=30),
                id='news_fetch_job',
                replace_existing=True
            )
            self.scheduler.start()
            self.running = True
            logger.info("Background worker started")

    def stop(self):
        """Stop the background worker"""
        if self.running:
            self.scheduler.shutdown()
            self.running = False
            logger.info("Background worker stopped")