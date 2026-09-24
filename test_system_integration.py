#!/usr/bin/env python3
"""
Integration test suite for the News Intelligence System.
Tests full end-to-end flows: authentication, preferences, feed, articles.

Usage:
  python test_system_integration.py
  
Requires: docker compose up --build (backend, frontend, mongodb running)
"""

import asyncio
import httpx
import json
import sys
import time
from datetime import datetime

# Configuration
API_URL = "http://localhost:8080"
FRONTEND_URL = "http://localhost:3000"
MONGO_URL = "mongodb://localhost:27017"

# Test user credentials
TEST_USER_EMAIL = "integration_test@example.com"
TEST_USER_NAME = "Integration Test User"
TEST_USER_PASSWORD = "TestPassword123!@#"

class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def log_test(test_name, passed, message=""):
    """Log test result with color."""
    status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if passed else f"{Colors.RED}✗ FAIL{Colors.RESET}"
    detail = f" — {message}" if message else ""
    print(f"  {status} {test_name}{detail}")
    return passed

def log_section(section_name):
    """Log test section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}→ {section_name}{Colors.RESET}")

def log_error(error_msg):
    """Log error message."""
    print(f"{Colors.RED}  ERROR: {error_msg}{Colors.RESET}")

async def test_health():
    """Test backend health endpoint."""
    log_section("Health Check")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_URL}/api/health")
            passed = response.status_code == 200
            log_test("Backend health check", passed, f"Status {response.status_code}")
            return passed
    except Exception as e:
        log_error(f"Health check failed: {e}")
        return False

async def test_auth_flow():
    """Test user registration and login."""
    log_section("Authentication")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test 1: Register new user
        try:
            register_payload = {
                "name": TEST_USER_NAME,
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            }
            response = await client.post(
                f"{API_URL}/api/auth/register",
                json=register_payload
            )
            reg_passed = response.status_code in [200, 201, 400]  # 400 if already exists
            if response.status_code == 400:
                log_test("User registration", True, "User already exists (using existing)")
            else:
                log_test("User registration", reg_passed, f"Status {response.status_code}")
        except Exception as e:
            log_error(f"Registration failed: {e}")
            return False
        
        # Test 2: Login
        try:
            login_payload = {
                "username": TEST_USER_EMAIL,  # OAuth2PasswordRequestForm uses 'username'
                "password": TEST_USER_PASSWORD
            }
            response = await client.post(
                f"{API_URL}/api/auth/login",
                data=login_payload,  # OAuth2 form uses form data, not JSON
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            login_passed = response.status_code == 200
            log_test("User login", login_passed, f"Status {response.status_code}")
            
            if not login_passed:
                log_error(f"Response: {response.text}")
                return False
            
            token_data = response.json()
            token = token_data.get("access_token")
            if not token:
                log_error("No access token in response")
                return False
            
            # Test 3: Get current user (verify token works)
            auth_headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(
                f"{API_URL}/api/auth/me",
                headers=auth_headers
            )
            me_passed = response.status_code == 200
            log_test("Get current user", me_passed, f"Status {response.status_code}")
            
            if me_passed:
                user_data = response.json()
                print(f"    User: {user_data.get('email')} (ID: {user_data.get('id')})")
            
            return token if login_passed and me_passed else None
            
        except Exception as e:
            log_error(f"Login/Auth failed: {e}")
            return None

async def test_preferences(token):
    """Test topic preference updates."""
    log_section("User Preferences")
    
    if not token:
        log_test("Update preferences", False, "No token available")
        return False
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            auth_headers = {"Authorization": f"Bearer {token}"}
            
            # Test: Update preferences
            preferences_payload = {
                "preferred_topics": ["Technology", "AI", "Business"]
            }
            response = await client.put(
                f"{API_URL}/api/users/preferences",
                json=preferences_payload,
                headers=auth_headers
            )
            pref_passed = response.status_code in [200, 201]
            log_test("Update preferences", pref_passed, f"Status {response.status_code}")
            
            if pref_passed:
                user_data = response.json()
                topics = user_data.get("preferred_topics", [])
                print(f"    Topics: {', '.join(topics)}")
            
            return pref_passed
    except Exception as e:
        log_error(f"Preferences update failed: {e}")
        return False

async def test_articles(token):
    """Test article feed endpoints."""
    log_section("Articles & Feed")
    
    if not token:
        log_test("Get feed", False, "No token available")
        return False
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            auth_headers = {"Authorization": f"Bearer {token}"}
            
            # Test 1: Get feed
            response = await client.get(
                f"{API_URL}/api/articles/feed?limit=5",
                headers=auth_headers
            )
            feed_passed = response.status_code in [200, 404]  # 404 if no articles
            log_test("Get personalized feed", feed_passed, f"Status {response.status_code}")
            
            if response.status_code == 200:
                articles = response.json()
                print(f"    Found {len(articles)} articles")
                if articles:
                    print(f"    Sample: {articles[0].get('title', 'N/A')[:60]}...")
            
            # Test 2: Search articles
            response = await client.get(
                f"{API_URL}/api/articles?query=technology&limit=5",
                headers=auth_headers
            )
            search_passed = response.status_code in [200, 404]
            log_test("Search articles", search_passed, f"Status {response.status_code}")
            
            # Test 3: Trending
            response = await client.get(
                f"{API_URL}/api/articles/trending?limit=5",
                headers=auth_headers
            )
            trending_passed = response.status_code in [200, 404]
            log_test("Get trending articles", trending_passed, f"Status {response.status_code}")
            
            return feed_passed and search_passed and trending_passed
    except Exception as e:
        log_error(f"Articles test failed: {e}")
        return False

async def test_bookmarks(token):
    """Test bookmarking functionality."""
    log_section("Bookmarks")
    
    if not token:
        log_test("Get bookmarks", False, "No token available")
        return False
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            auth_headers = {"Authorization": f"Bearer {token}"}
            
            # Test: Get bookmarks
            response = await client.get(
                f"{API_URL}/api/bookmarks",
                headers=auth_headers
            )
            bookmarks_passed = response.status_code in [200, 404]
            log_test("Get bookmarks", bookmarks_passed, f"Status {response.status_code}")
            
            return bookmarks_passed
    except Exception as e:
        log_error(f"Bookmarks test failed: {e}")
        return False

async def test_frontend():
    """Test frontend accessibility."""
    log_section("Frontend")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(FRONTEND_URL)
            frontend_passed = response.status_code == 200
            log_test("Frontend loads", frontend_passed, f"Status {response.status_code}")
            
            if frontend_passed:
                has_react = "react" in response.text.lower() or "index" in response.text.lower()
                log_test("React app detected", has_react)
            
            return frontend_passed
    except Exception as e:
        log_error(f"Frontend test failed: {e}")
        return False

async def run_all_tests():
    """Run complete integration test suite."""
    print(f"\n{Colors.BOLD}News Intelligence System - Integration Test Suite{Colors.RESET}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"API URL: {API_URL}")
    print(f"Frontend URL: {FRONTEND_URL}")
    print("=" * 60)
    
    results = {}
    
    # Run tests
    results["health"] = await test_health()
    results["auth"] = bool(await test_auth_flow())
    
    if results["auth"]:
        token = await test_auth_flow()
        if isinstance(token, str):
            results["preferences"] = await test_preferences(token)
            results["articles"] = await test_articles(token)
            results["bookmarks"] = await test_bookmarks(token)
    else:
        results["preferences"] = False
        results["articles"] = False
        results["bookmarks"] = False
    
    results["frontend"] = await test_frontend()
    
    # Summary
    print("\n" + "=" * 60)
    print(f"{Colors.BOLD}Test Summary{Colors.RESET}")
    
    for test_name, passed in results.items():
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if passed else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  {test_name}: {status}")
    
    total_passed = sum(1 for p in results.values() if p)
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ All tests passed!{Colors.RESET}")
        return 0
    else:
        print(f"{Colors.YELLOW}⚠ Some tests failed — see details above{Colors.RESET}")
        return 1

async def main():
    """Entry point."""
    # Wait for services to be ready
    print(f"\n{Colors.YELLOW}Waiting for services to be ready...{Colors.RESET}")
    for attempt in range(30):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{API_URL}/api/health")
                if response.status_code == 200:
                    print(f"{Colors.GREEN}Services ready!{Colors.RESET}")
                    break
        except:
            pass
        if attempt < 29:
            print(f"  Attempt {attempt + 1}/30 — retrying in 1s...")
            await asyncio.sleep(1)
    else:
        log_error("Services did not become ready after 30 seconds")
        return 1
    
    # Run tests
    return await run_all_tests()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
