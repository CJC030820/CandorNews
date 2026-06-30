from typing import List, Dict
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class DeduplicatorService:
    def __init__(self, similarity_threshold: float = 0.8):
        self.similarity_threshold = similarity_threshold

    def is_duplicate_url(self, url: str, existing_urls: List[str]) -> bool:
        return url in existing_urls

    def is_similar_title(self, title: str, existing_titles: List[str]) -> bool:
        for existing_title in existing_titles:
            if self.title_similarity(title, existing_title) >= self.similarity_threshold:
                return True
        return False

    def title_similarity(self, title1: str, title2: str) -> float:
        return SequenceMatcher(None, title1.lower(), title2.lower()).ratio()

    def remove_duplicates(self, articles: List[Dict]) -> List[Dict]:
        seen_urls = set()
        seen_titles = []
        unique_articles = []

        for article in articles:
            url = article.get("url")
            title = article.get("title", "")

            if not url or not title:
                continue

            if self.is_duplicate_url(url, seen_urls):
                logger.debug(f"Skipping duplicate URL: {url}")
                continue

            if self.is_similar_title(title, seen_titles):
                logger.debug(f"Skipping similar title: {title}")
                continue

            seen_urls.add(url)
            seen_titles.append(title)
            unique_articles.append(article)

        return unique_articles