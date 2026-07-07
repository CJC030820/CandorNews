#!/usr/bin/env python3
"""
Verification script to check that the news intelligence system components can be imported
and basic functionality works.
"""

import sys
import os

def test_imports():
    """Test that all key modules can be imported"""
    print("Testing imports...")

    try:
        # Add the backend directory to the path so we can import app modules
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

        # Test backend imports
        from app.services.news_fetcher import NewsFetcherService
        from app.services.trust_scorer import TrustScorerService
        from app.services.recommender import RecommenderService
        from app.services.keyword_extractor import KeywordExtractorService
        from app.services.storage import storage_service
        from app.worker import news_worker
        from app.main import app

        print("[OK] All backend imports successful")

        # Test instantiation
        news_fetcher = NewsFetcherService()
        trust_scorer = TrustScorerService()
        recommender = RecommenderService()
        keyword_extractor = KeywordExtractorService()

        print("[OK] All service instantiations successful")

        # Test that worker is initialized
        assert news_worker is not None
        print("[OK] News worker initialized")

        return True

    except Exception as e:
        print(f"[ERROR] Import error: {e}")
        return False

def test_environment():
    """Test that environment variables are set up correctly"""
    print("\nChecking environment...")

    # Check for .env file
    if os.path.exists('.env'):
        print("[OK] .env file found")
    else:
        print("[WARNING] .env file not found (copy from .env.example)")

    # Check for key environment variables
    env_vars = ['LD_SDK_KEY', 'NEWSAPI_KEY', 'GNEWS_API_KEY']
    for var in env_vars:
        if os.getenv(var):
            print(f"[OK] {var} is set")
        else:
            print(f"[INFO] {var} is not set (optional for some features)")

    return True

def main():
    print("Verifying News Intelligence System...\n")

    success = True
    success = test_imports() and success
    test_environment()

    if success:
        print("\n[SUCCESS] Verification passed! The system appears to be correctly configured.")
        print("\nNext steps:")
        print("1. Copy .env.example to .env and fill in your API keys")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Start MongoDB (or use Docker: docker-compose up -d mongodb)")
        print("4. Run the application: uvicorn app.main:app --reload")
        print("5. Check health endpoint: http://localhost:8080/health")
    else:
        print("\n[FAILED] Verification failed! Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()