from typing import List, Dict
import logging
import re

logger = logging.getLogger(__name__)

class TopicClassifierService:
    def __init__(self):
        # Define keywords for each topic
        self.topic_keywords = {
            "Technology": ["tech", "technology", "software", "hardware", "AI", "artificial intelligence", "machine learning", "computer", "internet", "gadget"],
            "Business": ["business", "economy", "finance", "market", "stock", "investment", "company", "industry", "trade"],
            "Politics": ["politics", "government", "election", "policy", "senate", "parliament", "minister", "president", "law"],
            "Sports": ["sport", "football", "basketball", "tennis", "olympics", "match", "team", "player", "game"],
            "Health": ["health", "medical", "medicine", "hospital", "disease", "virus", "vaccine", "fitness", "nutrition"],
            "AI": ["AI", "artificial intelligence", "machine learning", "deep learning", "neural network", "algorithm"],
            "Local Malaysia News": ["Malaysia", "Kuala Lumpur", "Jakarta", "Bandar", "Malaysian", "Mahathir", "Najib"],
            "Entertainment": ["entertainment", "movie", "film", "music", "celebrity", "Hollywood", "Bollywood", "TV"],
            "Finance": ["finance", "banking", "bank", "loan", "mortgage", "credit", "insurance", "fund"]
        }

    def classify_topic(self, title: str, description: str = "", content: str = "") -> str:
        text = f"{title} {description} {content}".lower()
        scores = {}
        for topic, keywords in self.topic_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in text:
                    score += 1
            scores[topic] = score

        # Get the topic with the highest score
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        else:
            return "General"