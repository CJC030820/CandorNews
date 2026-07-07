import sys
import traceback
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

modules = [
    'app.services.news_fetcher',
    'app.services.trust_scorer',
    'app.services.recommender',
    'app.services.keyword_extractor',
    'app.services.storage',
    'app.worker',
    'app.main'
]

for mod in modules:
    try:
        __import__(mod)
        print(f"OK: {mod}")
    except Exception as e:
        print(f"FAILED: {mod}")
        traceback.print_exc()
        break
