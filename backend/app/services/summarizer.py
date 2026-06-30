from typing import List, Dict
import logging
import re

logger = logging.getLogger(__name__)

class SummarizerService:
    def __init__(self, max_sentences: int = 4):
        self.max_sentences = max_sentences

    def summarize(self, text: str) -> str:
        if not text:
            return ""

        # Simple sentence split by punctuation
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # Take first few sentences
        summary_sentences = sentences[:self.max_sentences]
        summary = '. '.join(summary_sentences)
        if summary and not summary.endswith('.'):
            summary += '.'
        return summary

    def summarize_article(self, article: Dict) -> str:
        # Use description if available, otherwise content excerpt
        description = article.get("description", "")
        content = article.get("content_excerpt", "") or article.get("content", "")

        if description:
            return self.summarize(description)
        elif content:
            return self.summarize(content)
        else:
            return "No summary available."