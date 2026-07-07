import sys
import traceback
sys.path.insert(0, '.')

try:
    from app.services.news_fetcher import NewsFetcherService
    print("news_fetcher: OK")
except Exception as e:
    print("news_fetcher: FAILED")
    traceback.print_exc()

try:
    from app.services.trust_scorer import TrustScorerService
    print("trust_scorer: OK")
except Exception as e:
    print("trust_scorer: FAILED")
    traceback.print_exc()

try:
    from app.services.recommender import RecommenderService
    print("recommender: OK")
except Exception as e:
    print("recommender: FAILED")
    traceback.print_exc()

try:
    from app.services.keyword_extractor import KeywordExtractorService
    print("keyword_extractor: OK")
except Exception as e:
    print("keyword_extractor: FAILED")
    traceback.print_exc()

try:
    from app.services.storage import storage_service
    print("storage: OK")
except Exception as e:
    print("storage: FAILED")
    traceback.print_exc()

try:
    from app.worker import news_worker
    print("worker: OK")
except Exception as e:
    print("worker: FAILED")
    traceback.print_exc()

try:
    from app.main import app
    print("main: OK")
except Exception as e:
    print("main: FAILED")
    traceback.print_exc()