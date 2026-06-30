from typing import List, Dict, Any
import logging
from app.core.config import settings
from app.services.storage import storage_service

logger = logging.getLogger(__name__)

class RecommenderService:
    def __init__(self):
        self.weights = {
            "topic_preference_match": 0.35,
            "article_freshness": 0.20,
            "user_interaction_similarity": 0.15,
            "trust_score": 0.15,
            "keyword_similarity": 0.10,
            "source_preference": 0.05
        }

    def calculate_topic_preference_match(self, article_topic: str, user_preferred_topics: List[str]) -> float:
        if not user_preferred_topics:
            return 0.5
        if article_topic in user_preferred_topics:
            return 1.0
        # Partial match: if article topic is General, give lower score
        if article_topic == "General":
            return 0.3
        return 0.0

    def calculate_article_freshness(self, published_date: Any) -> float:
        # Simpler: newer articles get higher score
        # In reality, we would use a decay function
        from datetime import datetime, timezone
        if isinstance(published_date, str):
            # Try to parse
            try:
                published_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
            except:
                return 0.5
        elif not isinstance(published_date, datetime):
            return 0.5

        now = datetime.now(timezone.utc)
        diff = now - published_date
        # Assume freshness decreases linearly over 7 days
        days_diff = diff.days
        if days_diff < 0:
            return 1.0  # Future date, treat as fresh
        if days_diff > 7:
            return 0.0
        return 1.0 - (days_diff / 7.0)

    def calculate_user_interaction_similarity(self, user_id: str, article_id: str) -> float:
        # Calculate similarity based on user's past interactions with similar articles
        try:
            # Get user's interaction history
            user_interactions = list(storage_service.interactions.find({"user_id": user_id}))
            if not user_interactions:
                return 0.5  # No history, return neutral

            # Get the article we're scoring
            target_article = storage_service.articles.find_one({"_id": article_id})
            if not target_article:
                return 0.5

            # Calculate similarity based on topic and source
            target_topic = target_article.get("topic", "General")
            target_source = target_article.get("source", "")

            # Find articles the user has interacted with
            interacted_article_ids = [str(interaction["article_id"]) for interaction in user_interactions]
            interacted_articles = list(storage_service.articles.find({"_id": {"$in": interacted_article_ids}}))

            if not interacted_articles:
                return 0.5

            # Calculate average similarity
            topic_matches = sum(1 for art in interacted_articles if art.get("topic") == target_topic)
            source_matches = sum(1 for art in interacted_articles if art.get("source") == target_source)

            topic_similarity = topic_matches / len(interacted_articles) if interacted_articles else 0
            source_similarity = source_matches / len(interacted_articles) if interacted_articles else 0

            # Combine similarities
            return (topic_similarity * 0.7 + source_similarity * 0.3) if interacted_articles else 0.5

        except Exception as e:
            logger.error(f"Error calculating user interaction similarity: {e}")
            return 0.5

    def calculate_trust_score_component(self, trust_score: float) -> float:
        # Normalize trust score (0-100) to 0-1
        return trust_score / 100.0

    def calculate_keyword_similarity(self, article_keywords: List[str], user_interest_keywords: List[str]) -> float:
        # Calculate Jaccard similarity between article keywords and user interest keywords
        if not article_keywords and not user_interest_keywords:
            return 0.5
        if not article_keywords or not user_interest_keywords:
            return 0.0

        set1 = set(article_keywords)
        set2 = set(user_interest_keywords)

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        return intersection / union if union > 0 else 0.0

    def calculate_source_preference(self, article_source: str, user_preferred_sources: List[str]) -> float:
        # Calculate preference based on user's historical source preferences
        if not user_preferred_sources:
            return 0.5
        if article_source in user_preferred_sources:
            return 1.0
        return 0.0

    def recommend_articles(self, user_id: str, articles: List[Dict], limit: int = 10) -> List[Dict]:
        # Get user preferences
        user = storage_service.get_user_by_id(user_id)
        if not user:
            # If user not found, return articles sorted by trust score
            return sorted(articles, key=lambda x: x.get("trust_score", 0), reverse=True)[:limit]

        user_preferred_topics = user.preferred_topics or []
        # For simplicity, we'll assume user_preferred_sources and keywords are empty
        # In a real implementation, these would come from user profile or interaction history
        user_preferred_sources = []  # TODO: Implement user source preferences for
        user_interest_keywords = []  # TODO: Implement user

        scored_articles = []
        for article in articles:
            # Only consider completed articles
            if article.get("processing_status") != "completed":
                continue

            topic_match = self.calculate_topic_preference_match(
                article.get("topic", "General"),
                user_preferred_topics
            )
            freshness = self.calculate_article_freshness(
                article.get("published_date")
            )
            interaction_sim = self.calculate_user_interaction_similarity(
                user_id, article.get("id", "")
            )
            trust_comp = self.calculate_trust_score_component(
                article.get("trust_score", 0)
            )
            keyword_sim = self.calculate_keyword_similarity(
                article.get("keywords", []),
                user_interest_keywords
            )
            source_pref = self.calculate_source_preference(
                article.get("source", ""),
                user_preferred_sources
            )

            score = (
                self.weights["topic_preference_match"] * topic_match +
                self.weights["article_freshness"] * freshness +
                self.weights["user_interaction_similarity"] * interaction_sim +
                self.weights["trust_score"] * trust_comp +
                self.weights["keyword_similarity"] * keyword_sim +
                self.weights["source_preference"] * source_pref
            )

            article_with_score = article.copy()
            article_with_score["recommendation_score"] = score
            scored_articles.append(article_with_score)

        # Sort by score descending
        scored_articles.sort(key=lambda x: x["recommendation_score"], reverse=True)
        return scored_articles[:limit]

    def generate_recommendation_explanation(self, article: Dict, user_id: str) -> str:
        user = storage_service.get_user_by_id(user_id)
        if not user:
            return "Recommended based on high trust score and recent publication."

        explanations = []
        if article.get("topic", "General") in (user.preferred_topics or []):
            explanations.append(f"matches your {article.get('topic')} interest")
        # Add more explanation components as needed
        if not explanations:
            explanations.append("has a high trust score")
        if self.calculate_article_freshness(article.get("published_date")) > 0.7:
            explanations.append("was published recently")

        return "Recommended because this article " + ", ".join(explanations) + "."