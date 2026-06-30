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

    def analyze_article_sentiment(self, article: Dict) -> Dict[str, any]:
        title = article.get("title", "")
        description = article.get("description", "")
        content = article.get("content_excerpt", "") or article.get("content", "")
        text = f"{title} {description} {content}"

        scores = self.analyze_sentiment(text)
        label = self.get_sentiment_label(scores)

        return {
            "sentiment": label,
            "sentiment_score": scores["compound"]
        }