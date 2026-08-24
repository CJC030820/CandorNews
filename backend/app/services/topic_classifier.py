from typing import List, Dict
import logging
import re

logger = logging.getLogger(__name__)

MAX_CATEGORIES_PER_ARTICLE = 3


class TopicClassifierService:
    def __init__(self):
        # Define keywords for each topic. Keys are the canonical category
        # names shown in the UI. Matching uses whole-word boundaries (see
        # _count_keyword_matches) so short/ambiguous keywords like "AI"
        # don't false-positive match substrings inside unrelated words
        # (e.g. "said", "detail", "obtained", "mainly" all contain "ai").
        self.topic_keywords = {
            "Crime": [
                "crime", "criminal", "murder", "murdered", "robbery", "robbed",
                "theft", "stolen", "steal", "arrest", "arrested", "police",
                "court", "jail", "prison", "sentenced", "charged", "convicted",
                "trafficking", "assault", "kidnap", "kidnapping", "fraud",
                "scam", "smuggling", "homicide", "victim", "suspect",
                "investigation", "detained", "custody", "gang", "syndicate",
                "burglary", "extortion", "molest", "rape", "abuse", "stabbed",
                "shooting", "gunman", "raid", "drug bust", "corruption",
                "bribery", "money laundering"
            ],
            "Technology": ["tech", "technology", "software", "hardware", "artificial intelligence", "machine learning", "computer", "internet", "gadget", "app", "smartphone", "startup"],
            "Business": ["business", "economy", "finance", "market", "stock", "investment", "company", "industry", "trade"],
            "Politics": ["politics", "government", "election", "policy", "senate", "parliament", "minister", "president", "cabinet", "parti", "lawmaker"],
            "Sports": ["sport", "football", "basketball", "tennis", "olympics", "match", "team", "player", "tournament", "championship"],
            "Health": ["health", "medical", "medicine", "hospital", "disease", "virus", "vaccine", "fitness", "nutrition", "patient"],
            "AI": ["artificial intelligence", "machine learning", "deep learning", "neural network", "chatbot", "generative ai", "large language model"],
            "Local Malaysia News": ["malaysia", "kuala lumpur", "putrajaya", "malaysian", "sabah", "sarawak", "selangor", "penang", "johor"],
            "Entertainment": ["entertainment", "movie", "film", "music", "celebrity", "hollywood", "bollywood", "concert", "actress", "actor"],
            "Finance": ["banking", "bank", "loan", "mortgage", "credit", "insurance", "fund", "interest rate", "inflation"]
        }

        # Pre-compile a whole-word/whole-phrase regex per keyword for speed
        # and to guarantee consistent boundary matching.
        self._keyword_patterns = {
            topic: [
                (keyword, re.compile(r"\b" + re.escape(keyword.lower()) + r"\b"))
                for keyword in keywords
            ]
            for topic, keywords in self.topic_keywords.items()
        }

    def _score_topics(self, text: str) -> Dict[str, int]:
        text = text.lower()
        scores = {}
        for topic, patterns in self._keyword_patterns.items():
            score = 0
            for _keyword, pattern in patterns:
                if pattern.search(text):
                    score += 1
            scores[topic] = score
        return scores

    def classify_topics(self, title: str, description: str = "", content: str = "", max_categories: int = MAX_CATEGORIES_PER_ARTICLE) -> List[str]:
        """Return up to `max_categories` topics that best match the article,
        ranked by keyword match strength. Falls back to ["General"] if no
        topic scored above zero."""
        text = f"{title} {description} {content}"
        scores = self._score_topics(text)

        ranked = sorted(
            (topic for topic, score in scores.items() if score > 0),
            key=lambda t: scores[t],
            reverse=True
        )

        if not ranked:
            return ["General"]

        return ranked[:max_categories]

    def classify_topic(self, title: str, description: str = "", content: str = "") -> str:
        """Backward-compatible single-topic classification (returns the
        single best-matching topic). Prefer classify_topics() for new code."""
        return self.classify_topics(title, description, content, max_categories=1)[0]
