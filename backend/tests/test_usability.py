"""Executable service checks; human usability evaluation is a separate study."""
from app.services.summarizer import SummarizerService
from app.services.topic_classifier import TopicClassifierService
from app.services.sentiment_analyzer import SentimentAnalyzerService
from app.services.storage import storage_service
from app.models.user import UserCreate

def test_leading_sentence_summary():
    service=SummarizerService(max_sentences=2)
    assert service.summarize("First sentence. Second sentence! Third sentence?")=="First sentence. Second sentence."
    assert service.summarize("")==""

def test_topics():
    service=TopicClassifierService()
    assert "Sports" in service.classify_topics("Football team wins Premier League match", "", "")
    assert 1 <= len(service.classify_topics("Technology artificial intelligence business finance", "", "")) <= 3

def test_sentiment_polarity():
    service=SentimentAnalyzerService()
    assert service.analyze_article_sentiment({"title":"Wonderful excellent success"})["sentiment"]=="Positive"
    assert service.analyze_article_sentiment({"title":"Terrible disaster and horrible failure"})["sentiment"]=="Negative"

async def test_user_preferences_persist():
    await storage_service.create_user(UserCreate(name="Reader",email="reader@example.com",password="password123"))
    await storage_service.update_user_by_email("reader@example.com",{"preferred_topics":["Sports"]})
    assert (await storage_service.get_user_by_email("reader@example.com")).preferred_topics==["Sports"]
