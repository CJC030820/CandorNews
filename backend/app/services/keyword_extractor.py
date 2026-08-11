import logging
from typing import List

logger = logging.getLogger(__name__)


class KeywordExtractorService:
    """Lightweight keyword extraction (frequency-based, stopword-filtered).

    Deliberately avoids heavyweight NLP dependencies (spaCy models etc.) so
    the news ingestion pipeline stays fast and the Docker image small.
    """

    def __init__(self):
        pass

    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text using simple frequency analysis."""
        if not text or not text.strip():
            return []
        return self._extract_keywords_fallback(text, max_keywords)

    def _extract_keywords_fallback(self, text: str, max_keywords: int = 10) -> List[str]:
        import re
        from collections import Counter

        # Clean text
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = text.split()

        # Filter out common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'shall', 'can', 'this', 'that', 'these',
            'those', 'am', 'it', 'its', 'as', 'from', 'not', 'said', 'says'
        }

        # Filter words: not stop words, length > 2, alphabetic
        words = [w for w in words if w not in stop_words and len(w) > 2 and w.isalpha()]

        # Count frequency
        word_freq = Counter(words)

        # Return most common words
        return [word for word, _ in word_freq.most_common(max_keywords)]
