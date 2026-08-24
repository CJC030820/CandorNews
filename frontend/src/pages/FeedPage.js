import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import ArticleCard from '../components/ArticleCard';
import DarkModeToggle from '../components/DarkModeToggle';
import SuggestionPanel from '../components/SuggestionPanel';
import BackToTopButton from '../components/BackToTopButton';
import { useTrustedPlatforms } from '../context/TrustedPlatformsContext';
import './FeedPage.css';

const CATEGORY_ICONS = {
  'Local Malaysia News': '🇲🇾',
  'Politics': '🏛️',
  'Business': '💼',
  'Health': '🏥',
  'Technology': '💻',
  'AI': '🤖',
  'Entertainment': '🎬',
  'Finance': '💰',
  'Sports': '⚽',
  'Crime': '🚨',
  'General': '📰'
};

const formatRelativeDate = (isoString, now = Date.now()) => {
  if (!isoString) return '';
  const date = new Date(isoString);
  if (isNaN(date.getTime())) return isoString;
  const diffMs = now - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  if (diffSecs < 5) return 'Just now';
  if (diffSecs < 60) return `${diffSecs} second${diffSecs === 1 ? '' : 's'} ago`;
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 60) return `${diffMins} minute${diffMins === 1 ? '' : 's'} ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;
};

const FeedPage = ({ searchQuery, onSearchChange }) => {
  const { user, logout, getFeed, refreshFeed } = useAuth();
  const navigate = useNavigate();
  const [filter, setFilter] = useState('all');
  const [sortBy, setSortBy] = useState('recent');

  const [rawArticles, setRawArticles] = useState(() => {
    const stored = sessionStorage.getItem('feedArticles');
    return stored ? JSON.parse(stored) : [];
  });
  const [loading, setLoading] = useState(() => {
    const stored = sessionStorage.getItem('feedArticles');
    return !stored; // Only show loading if no cached articles
  });
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [nowTick, setNowTick] = useState(Date.now());
  const [isExiting, setIsExiting] = useState(false);
  
  // Track refresh progress and last refresh time
  const [refreshProgress, setRefreshProgress] = useState(0);
  const [lastRefreshTime, setLastRefreshTime] = useState(() => {
    const stored = localStorage.getItem('lastRefreshTime');
    return stored ? parseInt(stored, 10) : null;
  });

  const {
    platforms,
    isFollowing,
    toggleFollow,
    resetToDefaults
  } = useTrustedPlatforms();

  const [isManagingPlatforms, setIsManagingPlatforms] = useState(false);

  const loadFeed = useCallback(async () => {
    // Check if we have cached articles from a previous session
    const cached = sessionStorage.getItem('feedArticles');
    if (cached) {
      // Use cached articles, don't reload
      setLoading(false);
      return;
    }
    
    // Only fetch if no cache exists
    setError('');
    try {
      const data = await getFeed({ limit: 100 });
      const mapped = (data.articles || []).map((a) => ({
        id: a.id,
        title: a.title,
        source: a.source,
        rawDate: a.date,
        image: a.image,
        description: a.description,
        trustScore: a.trustScore,
        category: a.category,
        categories: (a.categories && a.categories.length > 0) ? a.categories : (a.category ? [a.category] : []),
        url: a.url,
        toneLabel: a.toneLabel || null
      }));
      setRawArticles(mapped);
      // Cache articles for quick return
      sessionStorage.setItem('feedArticles', JSON.stringify(mapped));
    } catch (err) {
      setError('Failed to load the latest news. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [getFeed]);

  useEffect(() => {
    // Load feed (uses cache if available)
    loadFeed();
    
    // Auto-refresh news in the background when page loads
    const autoRefreshNews = async () => {
      try {
        await refreshFeed();
        // After refresh completes, reload the feed to show latest articles
        await loadFeed();
      } catch (err) {
        console.error('Auto-refresh on page load failed:', err);
      }
    };
    
    // Trigger auto-refresh after a short delay to not block initial load
    const refreshTimer = setTimeout(() => {
      autoRefreshNews();
    }, 500);
    
    // Update last refresh time if not already set (first load)
    if (!lastRefreshTime) {
      const now = Date.now();
      setLastRefreshTime(now);
      localStorage.setItem('lastRefreshTime', now.toString());
    }
    
    return () => clearTimeout(refreshTimer);
  }, []);

  useEffect(() => {
    // Restore scroll position when returning to feed page
    const savedScrollPosition = sessionStorage.getItem('feedScrollPosition');
    if (savedScrollPosition) {
      setTimeout(() => {
        window.scrollTo(0, parseInt(savedScrollPosition, 10));
      }, 0);
      sessionStorage.removeItem('feedScrollPosition');
    }
  }, [rawArticles]); // Restore scroll after articles are rendered

  useEffect(() => {
    // Auto-refresh the feed every 5 minutes (manual refresh, not automatic page reload)
    const interval = setInterval(() => {
      // Clear cache on manual refresh to fetch new articles
      sessionStorage.removeItem('feedArticles');
    }, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Tick every second so "Last updated Xs/Xm ago" and article dates stay
    // accurate in real time without needing to re-fetch the feed.
    const tickInterval = setInterval(() => setNowTick(Date.now()), 1000);
    return () => clearInterval(tickInterval);
  }, []);
  
  // Helper to format "time ago" for last refresh
  // Shows "Just now" for the first 60 seconds, then starts counting minutes
  const getLastRefreshDisplay = () => {
    if (!lastRefreshTime) return 'Never';
    const diffMs = nowTick - lastRefreshTime;
    const diffSecs = Math.floor(diffMs / 1000);
    // Show "Just now" for first 60 seconds
    if (diffSecs < 60) return 'Just now';
    // After 60 seconds, start showing minutes
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  const handleManualRefresh = async () => {
    setRefreshing(true);
    setRefreshProgress(0);
    setError('');
    try {
      // Clear cached articles to force fresh fetch
      sessionStorage.removeItem('feedArticles');
      
      // Smooth progress simulation that never goes backwards
      // Progress increases gradually from 0 to 90% while waiting for API
      let currentProgress = 0;
      const progressInterval = setInterval(() => {
        setRefreshProgress(prev => {
          // Calculate next progress: add between 1-2% each interval for slower movement
          const increment = 1 + Math.random() * 1;
          const next = prev + increment;
          // Cap at 97% until refresh API completes
          return Math.min(next, 97);
        });
      }, 400); // Update every 400ms for smooth animation
      
      // Wait for the actual refresh to complete
      await refreshFeed();
      clearInterval(progressInterval);
      
      // Jump to 100% only when the API call completes
      setRefreshProgress(100);
      
      // Update last refresh time and save to localStorage
      const now = Date.now();
      setLastRefreshTime(now);
      localStorage.setItem('lastRefreshTime', now.toString());
      
      // Reload the feed with fresh data
      const data = await getFeed({ limit: 100 });
      const mapped = (data.articles || []).map((a) => ({
        id: a.id,
        title: a.title,
        source: a.source,
        rawDate: a.date,
        image: a.image,
        description: a.description,
        trustScore: a.trustScore,
        category: a.category,
        categories: (a.categories && a.categories.length > 0) ? a.categories : (a.category ? [a.category] : []),
        url: a.url,
        toneLabel: a.toneLabel || null
      }));
      setRawArticles(mapped);
      // Cache new articles
      sessionStorage.setItem('feedArticles', JSON.stringify(mapped));
    } catch (err) {
      setError('Failed to fetch the latest news right now. Please try again shortly.');
      setRefreshProgress(0); // Reset on error
    } finally {
      // Keep showing 100% for a moment, then fade out
      setTimeout(() => {
        setRefreshing(false);
        setRefreshProgress(0);
      }, 800);
    }
  };

  // Categories actually present in the fetched articles (falls back to a
  // sensible default list while loading). Since an article can belong to
  // up to 3 categories, flatten across the `categories` array.
  const availableCategories = Array.from(
    new Set(rawArticles.flatMap(a => a.categories && a.categories.length > 0 ? a.categories : [a.category]))
  ).filter(Boolean);

  // Filter by category (matches if the selected category is any of the
  // article's up-to-3 categories)
  const filteredArticles = filter === 'all'
    ? rawArticles
    : rawArticles.filter(a => (a.categories && a.categories.length > 0 ? a.categories : [a.category]).includes(filter));

  // Filter by search query
  const searchedArticles = searchQuery.trim() === ''
    ? filteredArticles
    : filteredArticles.filter(a =>
        a.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (a.description || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        a.source.toLowerCase().includes(searchQuery.toLowerCase())
      );

  // Sort articles
  const sortedArticles = [...searchedArticles].sort((a, b) => {
    if (sortBy === 'trust') {
      return (b.trustScore || 0) - (a.trustScore || 0);
    }
    return new Date(b.rawDate) - new Date(a.rawDate);
  });

  // Compute the live, ticking "X minutes ago" label at render time so it
  // stays accurate without needing to re-fetch the feed.
  const displayArticles = sortedArticles.map((a) => ({
    ...a,
    date: formatRelativeDate(a.rawDate, nowTick)
  }));

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleResetPlatforms = () => {
    if (window.confirm('Reset your followed platforms back to the default selection?')) {
      resetToDefaults();
    }
  };

  return (
    <div className={`feed-page ${isExiting ? 'fade-out' : 'fade-in'}`}>
      <BackToTopButton />
      <div className="feed-wrapper">
        <div className="sidebar">
          <div className="sidebar-section">
            <h3><span className="section-icon">📂</span> Categories</h3>
            <div className="sidebar-items">
              <button
                className={`sidebar-item ${filter === 'all' ? 'active' : ''}`}
                onClick={() => setFilter('all')}
              >
                <span className="icon">📰</span>
                <span className="text">All News</span>
              </button>
              {availableCategories.map(category => (
                <button
                  key={category}
                  className={`sidebar-item ${filter === category ? 'active' : ''}`}
                  onClick={() => setFilter(category)}
                >
                  <span className="icon">{CATEGORY_ICONS[category] || '📰'}</span>
                  <span className="text">{category}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="sidebar-section">
            <h3><span className="section-icon">🔄</span> Sort By</h3>
            <div className="sidebar-items">
              <button
                className={`sidebar-item ${sortBy === 'recent' ? 'active' : ''}`}
                onClick={() => setSortBy('recent')}
              >
                <span className="icon">⏱️</span>
                <span className="text">Most Recent</span>
              </button>
              <button
                className={`sidebar-item ${sortBy === 'trust' ? 'active' : ''}`}
                onClick={() => setSortBy('trust')}
              >
                <span className="icon">⭐</span>
                <span className="text">Most Trusted</span>
              </button>
            </div>
          </div>

          <div className="sidebar-section">
            <div className="sidebar-section-header">
              <h3><span className="section-icon">📡</span> Trusted Platforms</h3>
              <button
                className="manage-platforms-btn"
                onClick={() => setIsManagingPlatforms((prev) => !prev)}
                title={isManagingPlatforms ? 'Done managing' : 'Manage platforms'}
              >
                {isManagingPlatforms ? '✓ Done' : '⚙️ Manage'}
              </button>
            </div>

            <div className="platform-list">
              {platforms.map((platform) => {
                const following = isFollowing(platform.id);
                return (
                  <div key={platform.id} className="platform-item">
                    {isManagingPlatforms ? (
                      <>
                        <span className="platform-name">{platform.name}</span>
                        <button
                          className={`follow-toggle-btn ${following ? 'following' : ''}`}
                          onClick={() => toggleFollow(platform.id)}
                        >
                          {following ? '✓ Following' : '+ Follow'}
                        </button>
                      </>
                    ) : following ? (
                      <a
                        href={platform.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="following-item"
                      >
                        {platform.name}
                      </a>
                    ) : null}
                  </div>
                );
              })}

              {!isManagingPlatforms && platforms.every((p) => !isFollowing(p.id)) && (
                <p className="no-platforms-message">
                  You're not following any platforms yet. Click "⚙️ Manage" to follow some.
                </p>
              )}
            </div>

            {isManagingPlatforms && (
              <button
                type="button"
                className="reset-platforms-btn"
                onClick={handleResetPlatforms}
              >
                ↺ Reset to Defaults
              </button>
            )}
          </div>
        </div>

        <div className="main-content">
          <SuggestionPanel />

          <div className="feed-toolbar">
            <div className="refresh-controls">
              <button
                className="refresh-feed-btn"
                onClick={handleManualRefresh}
                disabled={refreshing}
                title="Fetch the latest news right now"
              >
                {refreshing ? (
                  <>
                    <span className="refresh-spinner" aria-hidden="true" />
                    Fetching...
                  </>
                ) : (
                  <>🔄 Refresh News</>
                )}
              </button>
              
              {refreshing && (
                <div className="refresh-progress-container">
                  <div className="progress-bar-wrapper">
                    <div 
                      className="progress-bar" 
                      style={{ width: `${Math.min(refreshProgress, 100)}%` }}
                    />
                  </div>
                </div>
              )}
              
              {!refreshing && lastRefreshTime && (() => {
                const diffMs = nowTick - lastRefreshTime;
                const diffHours = Math.floor(diffMs / 3600000);
                const diffDays = Math.floor(diffHours / 24);
                let statusClass = '';
                let icon = '✓';
                
                if (diffDays >= 1) {
                  statusClass = 'refresh-outdated-red';
                  icon = '!';
                } else if (diffHours >= 12) {
                  statusClass = 'refresh-outdated-yellow';
                  icon = '!';
                }
                
                return (
                  <div className={`last-refresh-info ${statusClass}`}>
                    <span className="refresh-icon">{icon}</span>
                    <span className="refresh-time">Last updated: {getLastRefreshDisplay()}</span>
                  </div>
                );
              })()}
            </div>
          </div>

          {error && <div className="feed-error">{error}</div>}

          {loading ? (
            <div className="feed-loading">
              <span className="feed-loading-icon">📡</span>
              <p>Fetching the latest news...</p>
            </div>
          ) : (
            <div className="articles-grid">
              {displayArticles.length > 0 ? (
                displayArticles.map(article => (
                  <ArticleCard key={article.id} article={article} />
                ))
              ) : (
                <div className="no-results">
                  <span className="no-results-icon">🔍</span>
                  <h3>No articles found</h3>
                  <p>Try adjusting your search or filters, or hit "Refresh News" to fetch the latest.</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FeedPage;
