import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import PageWrapper from '../components/PageWrapper';
import ArticleCard from '../components/ArticleCard';
import DarkModeToggle from '../components/DarkModeToggle';
import SuggestionPanel from '../components/SuggestionPanel';
import BackToTopButton from '../components/BackToTopButton';
import { useTrustedPlatforms } from '../context/TrustedPlatformsContext';
import { normalizeTopics } from '../constants/topics';
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
  'Sports': '🏆',
  'Crime': '🚨'
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

const getTitleWords = (title = '') => new Set(
  title.toLowerCase().replace(/[^a-z0-9\s]/g, '').split(/\s+/).filter((word) => word.length > 2)
);

const areSameStory = (firstTitle, secondTitle) => {
  const firstWords = getTitleWords(firstTitle);
  const secondWords = getTitleWords(secondTitle);
  const sharedWords = [...firstWords].filter((word) => secondWords.has(word)).length;
  return Math.min(firstWords.size, secondWords.size) > 0 && sharedWords / Math.min(firstWords.size, secondWords.size) >= 0.6;
};

const combineSimilarArticles = (articles) => {
  const groups = [];
  articles.forEach((article) => {
    const group = groups.find((candidate) => areSameStory(candidate[0].title, article.title));
    group ? group.push(article) : groups.push([article]);
  });
  return groups.map((group) => {
    const primary = group[0];
    const sources = [...new Set(group.map((article) => article.source).filter(Boolean))];
    return {
      ...primary,
      description: group.map((article) => article.description || '').sort((a, b) => b.length - a.length)[0] || '',
      source: sources.join(' • '),
      sources,
      platformReports: group.map((article) => ({ source: article.source, title: article.title, summary: article.description || '' })),
      isCombinedStory: sources.length > 1
    };
  });
};

const FeedPage = ({ searchQuery, onSearchChange }) => {
  const { user, logout, getFeed, refreshFeed } = useAuth();
    const selectedTopics = normalizeTopics(user?.preferred_topics || []);
  const navigate = useNavigate();
  const [filter, setFilter] = useState('all');

  const [rawArticles, setRawArticles] = useState(() => {
    const stored = sessionStorage.getItem('feedArticles');
    return stored ? combineSimilarArticles(JSON.parse(stored)) : [];
  });
  const [loading, setLoading] = useState(() => {
    const stored = sessionStorage.getItem('feedArticles');
    return !stored; // Only show loading if no cached articles
  });
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [nowTick, setNowTick] = useState(Date.now());
  const [isExiting, setIsExiting] = useState(false);
  
  const [refreshProgress, setRefreshProgress] = useState(0);
  const refreshProgressTimer = useRef(null);

  const stopRefreshProgress = () => {
    if (refreshProgressTimer.current) {
      clearInterval(refreshProgressTimer.current);
      refreshProgressTimer.current = null;
    }
  };

  const startRefreshProgress = () => {
    stopRefreshProgress();
    refreshProgressTimer.current = setInterval(() => {
      setRefreshProgress((previous) => {
        if (previous >= 92) return previous;
        const remaining = 92 - previous;
        return Math.min(92, previous + Math.max(0.4, remaining * 0.035));
      });
    }, 120);
  };

  const finishRefreshProgress = () => {
    stopRefreshProgress();
    setRefreshProgress((previous) => Math.max(previous, 92));
    const finishTimer = setInterval(() => {
      setRefreshProgress((previous) => {
        const next = previous + Math.max(3, (100 - previous) * 0.35);
        if (next >= 99.5) {
          clearInterval(finishTimer);
          return 100;
        }
        return next;
      });
    }, 45);
  };

  useEffect(() => () => stopRefreshProgress(), []);


  const {
    platforms,
    isFollowing,
    toggleFollow,
    resetToDefaults,
    followedPlatforms
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
      const data = await getFeed({ limit: 500 });
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
      setRawArticles(combineSimilarArticles(mapped));
      sessionStorage.setItem('feedArticles', JSON.stringify(mapped));
    } catch (err) {
      setError('Failed to load the latest news. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [getFeed]);

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
    const interval = setInterval(() => {
      if (!refreshing && followedPlatforms.length > 0) {
        handleManualRefresh();
      }
    }, 15 * 60 * 1000);
    return () => clearInterval(interval);
  }, [refreshing, followedPlatforms]);

  const handleManualRefresh = async () => {
    if (followedPlatforms.length === 0) {
      setError('Select at least one trusted platform before refreshing news.');
      return;
    }

    setRefreshing(true);
    setRefreshProgress(4);
    startRefreshProgress();
    setError('');
    try {
      sessionStorage.removeItem('feedArticles');
      const response = await refreshFeed(followedPlatforms.map((platform) => platform.name));
      setRefreshProgress((previous) => Math.max(previous, 60));

      const data = await getFeed({ limit: 100 });
      setRefreshProgress(85);
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
      setRawArticles(combineSimilarArticles(mapped));
      sessionStorage.setItem('feedArticles', JSON.stringify(mapped));
      finishRefreshProgress();
    } catch (err) {
      setError('Failed to fetch the latest news right now. Please try again shortly.');
      stopRefreshProgress();
      setRefreshProgress(0);
    } finally {
      setTimeout(() => {
        stopRefreshProgress();
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
  ).filter((category) => category && category !== 'General');

  // Filter by category (matches if the selected category is any of the
  // article's up-to-3 categories)
  const filteredArticles = followedPlatforms.length === 0
    ? []
    : (filter === 'all'
      ? rawArticles.filter((article) => followedPlatforms.some((platform) =>
          (article.source || '').toLowerCase().includes(platform.name.toLowerCase())
        ) && (selectedTopics.length === 0 || (article.categories || [article.category]).some((category) =>
          selectedTopics.some((topic) => category.toLowerCase() === topic.toLowerCase())
        )))
      : rawArticles.filter(a =>
          followedPlatforms.some((platform) =>
            (a.source || '').toLowerCase().includes(platform.name.toLowerCase())
          ) && (selectedTopics.length === 0 || (a.categories || [a.category]).some((category) =>
            selectedTopics.some((topic) => category.toLowerCase() === topic.toLowerCase())
          )) && (a.categories && a.categories.length > 0 ? a.categories : [a.category]).includes(filter)
        ));

  // Filter by search query
  const searchedArticles = searchQuery.trim() === ''
    ? filteredArticles
    : filteredArticles.filter(a =>
        a.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (a.description || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        a.source.toLowerCase().includes(searchQuery.toLowerCase())
      );

  // Sort articles
  const sortedArticles = [...searchedArticles].sort((a, b) => new Date(b.rawDate) - new Date(a.rawDate));

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
    <PageWrapper>
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
                <span className="text">News For You</span>
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
              <div className="refresh-button-wrapper">
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
              </div>
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
    </PageWrapper>
  );
};

export default FeedPage;
