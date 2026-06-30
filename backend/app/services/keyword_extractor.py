import logging
import spacy
from typing import List

logger = logging.getLogger(__name__)

class KeywordExtractorService:
    def __init__(self):
        """Initialize the keyword extractor with spaCy English model."""
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy English model not found. Attempting to download...")
            try:
                # Try to download the model
                import subprocess
                import sys
                subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("Successfully downloaded and loaded spaCy English model")
            except Exception as e:
                logger.error(f"Failed to download spaCy model: {e}")
                # Fallback to a simple keyword extraction method
                self.nlp = None

    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        Extract keywords from text using spaCy.

        Args:
            text: Input text to extract keywords from
            max_keywords: Maximum number of keywords to return

        Returns:
            List of extracted keywords
        """
        if not text or not text.strip():
            return []

        # If spaCy model is not available, use fallback method
        if self.nlp is None:
            return self._extract_keywords_fallback(text, max_keywords)

        try:
            # Process the text with spaCy
            doc = self.nlp(text.lower())

            # Extract nouns and proper nouns as potential keywords
            keywords = []
            for token in doc:
                # Include nouns, proper nouns, and adjectives that are not stop words
                if (token.pos_ in ["NOUN", "PROPN", "ADJ"] and
                    not token.is_stop and
                    not token.is_punct and
                    len(token.text) > 2):
                    keywords.append(token.lemma_)

            # Also extract noun phrases
            for chunk in doc.noun_chunks:
                # Clean up the noun phrase
                phrase = chunk.text.strip()
                if (len(phrase) > 2 and
                    not all(token.is_stop for token in chunk) and
                    not any(token.is_punct for token in chunk)):
                    keywords.append(phrase)

            # Remove duplicates while preserving order
            seen = set()
            unique_keywords = []
            for kw in keywords:
                if kw not in seen:
                    seen.add(kw)
                    unique_keywords.append(kw)

            # Return top keywords
            return unique_keywords[:max_keywords]

        except Exception as e:
            logger.error(f"Error extracting keywords with spaCy: {e}")
            return self._extract_keywords_fallback(text, max_keywords)

    def _extract_keywords_fallback(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        Fallback keyword extraction method when spaCy is not available.
        Simple approach: extract nouns based on capitalization and length.
        """
        import re

        # Clean text
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = text.split()

        # Filter out common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'shall', 'can', 'this', 'that', 'these',
            'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being'
        }

        # Filter words: not stop words, length > 2, alphabetic
        words = [w for w in words if w not in stop_words and len(w) > 2 and w.isalpha()]

        # Count frequency
        from collections import Counter
        word_freq = Counter(words)

        # Return most common words
        return [word for word, _ in word_freq.most_common(max_keywords)]