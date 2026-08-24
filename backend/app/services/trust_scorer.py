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
        """Score how strongly other independent sources corroborate this
        story. This is the main "is there evidence this actually happened"
        signal: zero when the story is single-source/unverified, and
        climbing toward 1.0 as more (and more reputable) independent outlets
        are found reporting the same story. Lack of corroboration should
        genuinely lower the score, not be treated as a neutral non-factor -
        otherwise unverified articles would outscore verified ones."""
        if not similar_articles:
            return 0.0

        credibility_scores = []
        for sim_article in similar_articles:
            source_domain = self.extract_domain(sim_article.get("url", ""))
            cred = await storage_service.get_source_credibility_by_domain(source_domain)
            credibility_scores.append(cred.credibility_score / 100.0 if cred else 0.5)

        avg_credibility = sum(credibility_scores) / len(credibility_scores)

        # Reward having *multiple* independent corroborating sources, not
        # just one. Diminishing returns after ~4 corroborating sources.
        count_bonus = min(len(similar_articles), 4) / 4.0

        # Blend: mostly driven by how credible the corroborating sources
        # are, with a boost for having several of them agree.
        score = (0.7 * avg_credibility) + (0.3 * count_bonus)
        return min(score, 1.0)

    def calculate_semantic_similarity(self, article: Dict, similar_articles: List[Dict]) -> float:
        if not similar_articles:
            return 0.0

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
        """Evaluate headline consistency with description/content.
        Improved scoring to give more credit to well-written articles:
        - If title is very short or empty, don't penalize heavily
        - Reward titles that have good keyword overlap (75%+ coverage = 1.0)
        - Reward titles with partial overlap (50%+ = 0.7+)
        - Only penalize if title has many unique words not in description"""
        title = article.get("title", "").lower()
        description = article.get("description", "").lower()
        
        # If no title or description, assume good (don't penalize)
        if not title or not description:
            return 0.8
        
        title_words = set(re.findall(r'\w+', title))
        desc_words = set(re.findall(r'\w+', description))
        
        # Empty title words - give benefit of the doubt
        if not title_words:
            return 0.9
        
        # Calculate overlap percentage
        overlap = len(title_words.intersection(desc_words))
        coverage = overlap / len(title_words)
        
        # More lenient scoring:
        # 75%+ = 1.0 (very consistent)
        # 50%+ = 0.8 (good consistency)
        # 25%+ = 0.6 (moderate consistency)
        # <25% = 0.4 (low consistency but not penalized heavily)
        if coverage >= 0.75:
            return 1.0
        elif coverage >= 0.50:
            return 0.85
        elif coverage >= 0.25:
            return 0.65
        else:
            return 0.45

    def calculate_metadata_completeness(self, article: Dict) -> float:
        """Calculate metadata completeness score.
        Improved to weight critical fields more heavily:
        - author (0.25) - shows journalistic attribution
        - published_date (0.25) - critical for news freshness
        - source (0.15) - outlet identity
        - description (0.20) - helps with semantic analysis
        - url (0.15) - allows verification
        Each field contributes proportionally to total (normalized to 1.0)"""
        field_weights = {
            "author": 0.25,
            "published_date": 0.25,
            "source": 0.15,
            "description": 0.20,
            "url": 0.15
        }
        
        score = 0.0
        for field, weight in field_weights.items():
            if article.get(field):
                score += weight
        
        return min(score, 1.0)

    def _score_and_label(self, source_rep: float, cross_src: float, sem_sim: float, head_cons: float, meta_comp: float) -> Dict[str, float]:
        """Shared scoring math used by both calculate_trust_score() and
        cold_start_fallback(), so cold-start (uncorroborated) articles are
        scored on the exact same scale as corroborated ones - just with
        cross_src=0 - instead of a separately renormalized formula that was
        previously letting unverified articles outscore verified ones."""
        score = (
            self.weights["source_reputation"] * source_rep +
            self.weights["cross_source"] * cross_src +
            self.weights["semantic_similarity"] * sem_sim +
            self.weights["headline_consistency"] * head_cons +
            self.weights["metadata_completeness"] * meta_comp
        ) * 100  # Convert to 0-100 scale

        # Cap at 95: no automated system should claim absolute (100%)
        # certainty that a story is true, but well-corroborated articles
        # from reputable outlets can now score very high.
        score = min(score, 95.0)

        if score >= 80:
            label = "High Trust"
        elif score >= 60:
            label = "Medium Trust"
        elif score >= 40:
            label = "Low Trust"
        else:
            label = "Needs Verification"

        return {"score": round(score, 2), "label": label}

    async def calculate_trust_score(self, article: Dict, similar_articles: List[Dict] = None) -> Dict[str, Any]:
        if similar_articles is None:
            similar_articles = []

        # Calculate each component
        source_rep = await self.calculate_source_reputation_async(self.extract_domain(article.get("url", "")))
        cross_src = await self.calculate_cross_source_verification(article, similar_articles)
        sem_sim = self.calculate_semantic_similarity(article, similar_articles)
        head_cons = self.calculate_headline_consistency(article)
        meta_comp = self.calculate_metadata_completeness(article)

        result = self._score_and_label(source_rep, cross_src, sem_sim, head_cons, meta_comp)

        # Generate explanation
        explanation = (
            f"Source Reputation: {source_rep:.2f}, "
            f"Cross-Source Verification: {cross_src:.2f} ({len(similar_articles)} corroborating source(s)), "
            f"Semantic Similarity: {sem_sim:.2f}, "
            f"Headline Consistency: {head_cons:.2f}, "
            f"Metadata Completeness: {meta_comp:.2f}"
        )

        return {
            "trust_score": result["score"],
            "trust_label": result["label"],
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
        """Score an article with no corroborating sources found (yet).
        Uses the exact same weighted formula as calculate_trust_score(),
        with cross_source and semantic_similarity explicitly at 0 - so lack
        of corroboration genuinely caps the achievable score, rather than
        renormalizing weights across fewer components (which previously let
        unverified single-source articles outscore verified, corroborated
        ones)."""
        source_rep = await self.calculate_source_reputation_async(self.extract_domain(article.get("url", "")))
        head_cons = self.calculate_headline_consistency(article)
        meta_comp = self.calculate_metadata_completeness(article)

        result = self._score_and_label(source_rep, 0.0, 0.0, head_cons, meta_comp)

        explanation = (
            f"No corroborating sources found yet (single-source/cold-start): "
            f"Source Reputation: {source_rep:.2f}, "
            f"Headline Consistency: {head_cons:.2f}, "
            f"Metadata Completeness: {meta_comp:.2f}"
        )

        return {
            "trust_score": result["score"],
            "trust_label": result["label"],
            "trust_explanation": explanation,
            "components": {
                "source_reputation": source_rep,
                "cross_source_verification": 0.0,
                "semantic_similarity": 0.0,
                "headline_consistency": head_cons,
                "metadata_completeness": meta_comp
            }
        }
