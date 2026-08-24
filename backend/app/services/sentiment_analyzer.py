from typing import Dict
import logging
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)

class SentimentAnalyzerService:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()

    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        if not text:
            return {"compound": 0.0, "pos": 0.0, "neu": 0.0, "neg": 0.0}
        return self.analyzer.polarity_scores(text)

    def get_sentiment_label(self, sentiment_scores: Dict[str, float]) -> str:
        compound = sentiment_scores["compound"]
        if compound >= 0.05:
            return "Positive"
        elif compound <= -0.05:
            return "Negative"
        else:
            return "Neutral"

    def get_tone_label(self, sentiment_scores: Dict[str, float]) -> str:
        """Classify how emotionally-charged/opinionated the writing is.
        
        More stringent thresholds to ensure only truly emotionally loaded content
        is flagged as such. Uses multiple factors:
        - neu (neutral wording ratio): tracks objective vs emotional language
        - pos/neg (positive/negative word intensity): measures emotional charge
        - compound (overall sentiment strength): measures opinion intensity
        
        Requires sustained emotional language throughout, not just isolated words.
        """
        neu = sentiment_scores.get("neu", 1.0)
        pos = sentiment_scores.get("pos", 0.0)
        neg = sentiment_scores.get("neg", 0.0)
        compound = sentiment_scores.get("compound", 0.0)
        
        # Calculate emotional intensity (how much non-neutral content exists)
        emotional_intensity = pos + neg  # Sum of positive and negative sentiment word ratios
        absolute_compound = abs(compound)  # How strong the overall sentiment is
        
        # Stricter thresholds for emotional content detection
        # "Emotionally Charged" = sustained emotional language throughout
        # Requires: mostly non-neutral wording AND strong sentiment intensity
        if neu <= 0.70 and emotional_intensity >= 0.20 and absolute_compound >= 0.45:
            return "Emotionally Charged"
        # "Mildly Emotional" = some emotional language but mostly objective
        # Requires: moderate non-neutral wording AND moderate sentiment
        elif neu <= 0.82 and emotional_intensity >= 0.12 and absolute_compound >= 0.25:
            return "Mildly Emotional"
        # "Neutral / Objective" = primarily factual/objective reporting
        else:
            return "Neutral / Objective"

    def analyze_article_sentiment(self, article: Dict) -> Dict[str, any]:
        title = article.get("title", "")
        description = article.get("description", "")
        content = article.get("content_excerpt", "") or article.get("content", "")
        text = f"{title} {description} {content}"

        scores = self.analyze_sentiment(text)
        label = self.get_sentiment_label(scores)
        tone = self.get_tone_label(scores)

        return {
            "sentiment": label,
            "sentiment_score": scores["compound"],
            "tone_label": tone
        }