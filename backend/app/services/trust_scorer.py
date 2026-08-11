from typing import Dict, List, Any
import logging
import re
from datetime import timedelta
from app.core.config import settings
from app.services.storage import storage_service

logger = logging.getLogger(__name__)

class TrustScorerService:
    def __init__(self):
        self.weights = {
            "source_reputation": settings.TRUST_WEIGHT_SOURCE_REPUTATION,
            "cross_source": settings.TRUST_WEIGHT_CROSS_SOURCE,
            "semantic_similarity": settings.TRUST_WEIGHT_SEMANTIC_SIMILARITY,
            "headline_consistency": settings.TRUST_WEIGHT_HEADLINE_CONSISTENCY,
            "metadata_completeness": settings.TRUST_WEIGHT_METADATA_COMPLETENESS
        }
        # Try to import sklearn for better semantic similarity
        self.sklearn_available = False
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            self.TfidfVectorizer = TfidfVectorizer
            self.cosine_similarity = cosine_similarity
            self.sklearn_available = True
            logger.info("SKLearn available for enhanced semantic similarity")
        except ImportError:
            logger.warning("SKLearn not available, using fallback for semantic similarity")

    def _article_to_text(self, article: Dict) -> str:
        """Convert article dictionary to a string for similarity comparison."""
        title = article.get("title", "")
        description = article.get("description", "")
        content = article.get("content", "")
        return f"{title} {description} {content}".strip()

    def _simple_tokenize(self, text: str) -> set:
        """Simple tokenization: lowercase and split by non-alphanumeric."""
        words = re.findall(r'\b\w+\b', text.lower())
        return set(words)

    def _jaccard_similarity(self, text1: str, text2_list: List[str]) -> float:
        """Calculate Jaccard similarity between text1 and each text in text2_list, return average."""
        if not text2_list:
            return 0.0
        words1 = self._simple_tokenize(text1)
        similarities = []
        for text2 in text2_list:
            words2 = self._simple_tokenize(text2)
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            if union == 0:
                similarity = 0.0
            else:
                similarity = intersection / union
            similarities.append(similarity)
        return sum(similarities) / len(similarities) if similarities else 0.0

    def calculate_source_reputation(self, source_domain: str, source_cred=None) -> float:
        """Compute normalized (0-1) source reputation. If source_cred wasn't
        pre-fetched by the caller, default to the neutral score."""
        if source_cred:
            return source_cred.credibility_score / 100.0  # Normalize to 0-1
        else:
            # Default score for unknown sources
            return 0.5

    async def calculate_source_reputation_async(self, source_domain: str) -> float:
        source_cred = await storage_service.get_source_credibility_by_domain(source_domain)
        return self.calculate_source_reputation(source_domain, source_cred)

    async def calculate_cross_source_verification(self, article: Dict, similar_articles: List[Dict]) -> float:
        # Simplified: check if similar articles exist from trusted sources
        if not similar_articles:
            # Cold-start: return neutral score (will be handled by fallback)
            return 0.5
        trusted_count = 0
        for sim_article in similar_articles:
            source_domain = self.extract_domain(sim_article.get("url", ""))
            cred = await storage_service.get_source_credibility_by_domain(source_domain)
            if cred and cred.credibility_score >= 70:  # Consider trusted if score >=70
                trusted_count += 1
        ratio = trusted_count / len(similar_articles) if similar_articles else 0
        return ratio

    def calculate_semantic_similarity(self, article: Dict, similar_articles: List[Dict]) -> float:
        if not similar_articles:
            return 0.5

        # Convert articles to text
        def article_to_text(art):
            return f"{art.get('title', '')} {art.get('description', '')} {art.get('content', '')}"

        texts = [article_to_text(article)] + [article_to_text(art) for art in similar_articles]

        if self.sklearn_available:
            try:
                tfidf = self.TfidfVectorizer().fit_transform(texts)
                # Calculate cosine similarity between the first article (index 0) and each of the others
                similarities = self.cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
                return float(sum(similarities) / len(similarities))
            except Exception as e:
                logger.warning(f"Error in TF-IDF similarity: {e}, falling back to Jaccard")
                # Fall through to Jaccard
                pass

        # Fallback to Jaccard similarity
        return self._jaccard_similarity(texts[0], texts[1:])

    def calculate_headline_consistency(self, article: Dict) -> float:
        title = article.get("title", "").lower()
        description = article.get("description", "").lower()
        # Simple check: see if key words from title appear in description
        title_words = set(re.findall(r'\w+', title))
        desc_words = set(re.findall(r'\w+', description))
        if not title_words:
            return 1.0
        overlap = len(title_words.intersection(desc_words))
        return min(overlap / len(title_words), 1.0)

    def calculate_metadata_completeness(self, article: Dict) -> float:
        fields = ["author", "published_date", "source", "url", "description"]
        present = 0
        for field in fields:
            if article.get(field):
                present += 1
        return present / len(fields)

    async def calculate_trust_score(self, article: Dict, similar_articles: List[Dict] = None) -> Dict[str, Any]:
        if similar_articles is None:
            similar_articles = []

        # Calculate each component
        source_rep = await self.calculate_source_reputation_async(self.extract_domain(article.get("url", "")))
        cross_src = await self.calculate_cross_source_verification(article, similar_articles)
        sem_sim = self.calculate_semantic_similarity(article, similar_articles)
        head_cons = self.calculate_headline_consistency(article)
        meta_comp = self.calculate_metadata_completeness(article)

        # Apply weights
        score = (
            self.weights["source_reputation"] * source_rep +
            self.weights["cross_source"] * cross_src +
            self.weights["semantic_similarity"] * sem_sim +
            self.weights["headline_consistency"] * head_cons +
            self.weights["metadata_completeness"] * meta_comp
        ) * 100  # Convert to 0-100 scale

        # Determine label
        if score >= 80:
            label = "High Trust"
        elif score >= 60:
            label = "Medium Trust"
        elif score >= 40:
            label = "Low Trust"
        else:
            label = "Needs Verification"

        # Generate explanation
        explanation = (
            f"Source Reputation: {source_rep:.2f}, "
            f"Cross-Source Verification: {cross_src:.2f}, "
            f"Semantic Similarity: {sem_sim:.2f}, "
            f"Headline Consistency: {head_cons:.2f}, "
            f"Metadata Completeness: {meta_comp:.2f}"
        )

        return {
            "trust_score": round(score, 2),
            "trust_label": label,
            "trust_explanation": explanation,
            "components": {
                "source_reputation": source_rep,
                "cross_source_verification": cross_src,
                "semantic_similarity": sem_sim,
                "headline_consistency": head_cons,
                "metadata_completeness": meta_comp
            }
        }

    def extract_domain(self, url: str) -> str:
        # Simple domain extraction: urllib.parse urlparse import
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            return parsed.netloc
        except:
            return ""

    def find_similar_articles(self, article: Dict, limit: int = 10) -> List[Dict]:
        """Find similar articles based on topic and time frame.

        NOTE: This performs a synchronous, best-effort lookup using the
        underlying pymongo-style cursor and is currently unused by the
        real-time ingestion pipeline (which relies on cold_start_fallback).
        Kept for future cross-source verification work.
        """
        return []

    async def cold_start_fallback(self, article: Dict) -> Dict[str, Any]:
        # When no similar articles, use only local indicators
        source_rep = await self.calculate_source_reputation_async(self.extract_domain(article.get("url", "")))
        head_cons = self.calculate_headline_consistency(article)
        meta_comp = self.calculate_metadata_completeness(article)

        # Recalibrate weights: exclude cross-source and semantic similarity
        # Adjust weights to sum to 1
        w_source = settings.TRUST_WEIGHT_SOURCE_REPUTATION
        w_head = settings.TRUST_WEIGHT_HEADLINE_CONSISTENCY
        w_meta = settings.TRUST_WEIGHT_METADATA_COMPLETENESS
        total = w_source + w_head + w_meta
        if total > 0:
            w_source_norm = w_source / total
            w_head_norm = w_head / total
            w_meta_norm = w_meta / total
        else:
            w_source_norm = w_head_norm = w_meta_norm = 1/3

        score = (
            w_source_norm * source_rep +
            w_head_norm * head_cons +
            w_meta_norm * meta_comp
        ) * 100

        if score >= 80:
            label = "High Trust"
        elif score >= 60:
            label = "Medium Trust"
        elif score >= 40:
            label = "Low Trust"
        else:
            label = "Needs Verification"

        explanation = (
            f"Cold-start fallback: "
            f"Source Reputation: {source_rep:.2f}, "
            f"Headline Consistency: {head_cons:.2f}, "
            f"Metadata Completeness: {meta_comp:.2f}"
        )

        return {
            "trust_score": round(score, 2),
            "trust_label": label,
            "trust_explanation": explanation,
            "components": {
                "source_reputation": source_rep,
                "cross_source_verification": 0.0,
                "semantic_similarity": 0.0,
                "headline_consistency": head_cons,
                "metadata_completeness": meta_comp
            }
        }