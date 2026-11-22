import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import ArticleCard from '../components/ArticleCard';
import DarkModeToggle from '../components/DarkModeToggle';
import SuggestionPanel from '../components/SuggestionPanel';
import BackToTopButton from '../components/BackToTopButton';
import { useTrustedPlatforms } from '../context/TrustedPlatformsContext';
import { useBookmarks } from '../context/BookmarkContext';
import { useReadArticles } from '../context/ReadArticlesContext';
import { rankForYou } from '../utils/personalRanking';
import './FeedPage.css';
import { RefreshIcon } from '../components/Icons';


const formatRelativeDate = (isoString, now = Date.now()) => {
  if (!isoString) return '';
  const date = new Date(isoString);
  if (isNaN(date.getTime())) return isoString;
  const diffMs = now - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Less than a minute ago';
  if (diffMins < 60) return `${diffMins} minute${diffMins === 1 ? '' : 's'} ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;
};

export const mapFeedArticle = article => ({...article, rawDate:article.date,
  categories:article.categories?.length ? article.categories : (article.category ? [article.category] : [])});

const NEAR_TOP_PX = 300;
const MINUTE_MS = 60 * 1000;
const SORT_KEY = 'feedSortMode';
const readSort = () => { try { return localStorage.getItem(SORT_KEY) === 'newest' ? 'newest' : 'foryou'; } catch { return 'foryou'; } };

const FeedPage = ({ searchQuery = '', onSearchChange }) => {
  const { user, logout, getFeed, refreshFeed, getRefreshStatus, selectedTopics, searchArticles } = useAuth();
  const { bookmarks = [] } = useBookmarks();
  const { history = [] } = useReadArticles();
  const [sortMode, setSortMode] = useState(readSort);
  const changeSort = (mode) => { setSortMode(mode); try { localStorage.setItem(SORT_KEY, mode); } catch { /* private mode */ } };
  // Server search over every stored article: { query, articles } or null.
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const navigate = useNavigate();
  const feedPageRef = useRef(null);
  const [filter, setFilter] = useState('all');

  const [rawArticles, setRawArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [nowTick, setNowTick] = useState(Date.now());
  const alive = useRef(true);
  const busy = useRef(false);
  const restoredScroll = useRef(false);
  // Background reloads must not insert articles above the reader: iPhone
  // Safari does not keep the scroll position when content is added above,
  // so the list would jump. New articles wait behind a "new articles" button.
  const articlesRef = useRef([]);
  const pendingArticles = useRef(null);
  const [pendingCount, setPendingCount] = useState(0);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);

  const {
    platforms,
    isFollowing,
    toggleFollow,
    resetToDefaults,
    followedPlatforms
  } = useTrustedPlatforms();

  const [isManagingPlatforms, setIsManagingPlatforms] = useState(false);

  const applyArticles = useCallback((articles) => {
    articlesRef.current = articles;
    pendingArticles.current = null;
    setPendingCount(0);
    setRawArticles(articles);
  }, []);

  const loadFeed = useCallback(async ({ background = false } = {}) => {
    try {
      const data = await getFeed({limit:500});
      if (!alive.current) return;
      const next = (data.articles || []).map(mapFeedArticle);
      const known = new Set(articlesRef.current.map((a) => a.id));
      const fresh = next.filter((a) => !known.has(a.id)).length;
      if (background && fresh > 0 && window.scrollY > NEAR_TOP_PX) {
        pendingArticles.current = next;
        setPendingCount(fresh);
      } else {
        applyArticles(next);
      }
    } catch { if (alive.current && !background) setError('Failed to load the latest news. Please try again.'); }
    finally { if (alive.current) setLoading(false); }
  }, [getFeed, applyArticles]);
  useEffect(() => { loadFeed(); }, [loadFeed]);

  const showPendingArticles = useCallback(() => {
    if (pendingArticles.current) applyArticles(pendingArticles.current);
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
  }, [applyArticles]);

  // Back near the top: show waiting articles without moving the page.
  useEffect(() => {
    if (!pendingCount) return undefined;
    const onScroll = () => {
      if (window.scrollY <= NEAR_TOP_PX && pendingArticles.current) applyArticles(pendingArticles.current);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, [pendingCount, applyArticles]);

  // Article times ("5 minutes ago") count in whole minutes, so they are
  // refreshed once a minute, on the minute (not every second).
  useEffect(() => {
    let tick;
    const align = setTimeout(() => {
      setNowTick(Date.now());
      tick = setInterval(() => setNowTick(Date.now()), MINUTE_MS);
    }, MINUTE_MS - (Date.now() % MINUTE_MS));
    // Returning to the tab shows up-to-date times at once.
    const onVisible = () => { if (document.visibilityState === 'visible') setNowTick(Date.now()); };
    document.addEventListener('visibilitychange', onVisible);
    return () => { clearTimeout(align); clearInterval(tick); document.removeEventListener('visibilitychange', onVisible); };
  }, []);

  // Check for newly collected articles every minute (nothing is downloaded if none are new).
  useEffect(() => {
    const reload = setInterval(() => loadFeed({ background: true }), MINUTE_MS);
    return () => clearInterval(reload);
  }, [loadFeed]);

  const handleManualRefresh = async () => {
    if (busy.current) return;
    if (!followedPlatforms.length) { setError('Select at least one platform.'); return; }
    busy.current = true; setRefreshing(true); setError('');
    try {
      const job = await refreshFeed(followedPlatforms.map(platform => platform.name));
      let finished = false;
      for (let attempt = 0; attempt < 120 && alive.current; attempt += 1) {
        const status = await getRefreshStatus(job.jobId);
        if (status.status === 'failed') throw new Error('Refresh failed. Please retry.');
        if (status.status === 'completed') { finished = true; break; }
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
      if (alive.current) {
        await loadFeed();
        if (!finished) setError('Refresh is still running. The feed checks for new articles every minute.');
      }
    } catch (err) { if (alive.current) setError(err.message || 'Refresh failed. Please retry.'); }
    finally { busy.current = false; if (alive.current) setRefreshing(false); }
  };

  // Searching looks through every stored article on the server, not only
  // the latest batch loaded here (waits until typing pauses).
  const query = searchQuery.trim();
  const searchRef = useRef(searchArticles);
  searchRef.current = searchArticles;
  useEffect(() => {
    if (query.length < 2 || !searchRef.current) { setSearchResults(null); setSearching(false); return undefined; }
    let active = true;
    setSearching(true);
    const timer = setTimeout(() => {
      searchRef.current(query, 200)
        .then((data) => { if (active) setSearchResults({ query, total: data.total, articles: (data.articles || []).map(mapFeedArticle) }); })
        .catch(() => { if (active) setSearchResults(null); })
        .finally(() => { if (active) setSearching(false); });
    }, 350);
    return () => { active = false; clearTimeout(timer); };
  }, [query]);

  // Categories actually present in the fetched articles (falls back to a
  // sensible default list while loading). Since an article can belong to
  // up to 3 categories, flatten across the `categories` array.
  const availableCategories = useMemo(() => {
    return Array.from(
      new Set(rawArticles.flatMap(a => a.categories && a.categories.length > 0 ? a.categories : [a.category]))
    ).filter(Boolean);
  }, [rawArticles]);

  // Filter by category (matches if the selected category is any of the
  // article's up-to-3 categories). "News For You" ('all') shows articles in
  // any of the user's interests, and updates as soon as the interests change.
  const interestKey = (selectedTopics || []).join('|');
  const searchActive = query !== '';
  const serverMatches = searchResults && searchResults.query === query ? searchResults.articles : null;
  const serverTotal = serverMatches ? searchResults.total : null;

  // A search looks through every category, so a suggestion's count matches
  // what is shown; the category view comes back when the search is cleared.
  const wasSearching = useRef(false);
  useEffect(() => {
    if (searchActive && !wasSearching.current) setFilter('all');
    wasSearching.current = searchActive;
  }, [searchActive]);
  const filteredArticles = useMemo(() => {
    const interests = interestKey ? interestKey.split('|') : [];
    const categoriesOf = (a) => (a.categories && a.categories.length > 0 ? a.categories : [a.category]);
    // While searching, include matches from all stored articles.
    const seen = new Set(rawArticles.map((a) => a.id));
    const pool = serverMatches ? [...rawArticles, ...serverMatches.filter((a) => !seen.has(a.id))] : rawArticles;
    const trustedArticles = pool.filter((article) =>
      followedPlatforms.some((platform) =>
        (article.source || '').toLowerCase().includes(platform.name.toLowerCase())
      )
    );
    if (filter !== 'all') return trustedArticles.filter(a => categoriesOf(a).includes(filter));
    // A search under News For You looks beyond the chosen interests.
    return interests.length && !searchActive
      ? trustedArticles.filter(a => categoriesOf(a).some(category => interests.includes(category)))
      : trustedArticles;
  }, [rawArticles, serverMatches, searchActive, filter, followedPlatforms, interestKey]);

  // After interests are saved, show the updated "News For You" list.
  const handleInterestsSaved = useCallback(() => {
    setFilter('all');
    feedPageRef.current?.querySelector('.feed-toolbar')?.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
  }, []);

  // Filter by search query
  // Same rule as the server search: every word starts a word somewhere in the
  // headline, summary or publisher ("ring" finds "ringgit", not "during").
  // Articles the server found are kept as is.
  const searchedArticles = useMemo(() => {
    const words = query.split(/\s+/).filter(Boolean);
    if (!words.length) return filteredArticles;
    const patterns = words.map((w) => new RegExp(`\\b${w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`, 'i'));
    const fromServer = new Set((serverMatches || []).map((a) => a.id));
    return filteredArticles.filter((a) => {
      if (fromServer.has(a.id)) return true;
      const text = `${a.title || ''} ${a.description || ''} ${a.source || ''}`;
      return patterns.every((p) => p.test(text));
    });
  }, [filteredArticles, query, serverMatches]);

  // News For You: personal order from reading history and bookmarks
  // (falls back to newest first). Other views and searches: newest first.
  const personalOn = filter === 'all' && !searchActive && sortMode === 'foryou';
  const { sortedArticles, personalised } = useMemo(() => {
    if (personalOn) {
      const ranked = rankForYou(searchedArticles, history, bookmarks);
      return { sortedArticles: ranked.articles, personalised: ranked.personalised };
    }
    return { sortedArticles: [...searchedArticles].sort((a, b) => new Date(b.rawDate) - new Date(a.rawDate)), personalised: false };
  }, [searchedArticles, personalOn, history, bookmarks]);

  // Compute the live, ticking "X minutes ago" label at render time so it
  // stays accurate without needing to re-fetch the feed.
  const displayArticles = useMemo(() => {
    return sortedArticles.map((a) => ({
      ...a,
      date: formatRelativeDate(a.rawDate, nowTick)
    }));
  }, [sortedArticles, nowTick]);

  // Restore the feed position after its cards exist in the DOM.
  useEffect(() => {
    if (loading || restoredScroll.current) return;
    const savedPosition = Number(sessionStorage.getItem('feedScrollPosition'));
    if (!Number.isFinite(savedPosition) || savedPosition < 0) {
      restoredScroll.current = true;
      return;
    }

    const frame = requestAnimationFrame(() => {
      window.scrollTo({ top: savedPosition, left: 0, behavior: 'auto' });
      restoredScroll.current = true;
    });
    return () => cancelAnimationFrame(frame);
  }, [loading, displayArticles.length]);

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
    <div ref={feedPageRef} className="feed-page">
      <BackToTopButton />
      {pendingCount > 0 && (
        <button type="button" className="new-articles-pill" onClick={showPendingArticles}>
          {pendingCount} new article{pendingCount === 1 ? '' : 's'}
        </button>
      )}
      <div className="feed-wrapper">
        <div className="sidebar">
          <div className="sidebar-section" data-guide="categories">
            <h3>Categories</h3>
            <div className="sidebar-items">
              <button
                className={`sidebar-item ${filter === 'all' ? 'active' : ''}`}
                onClick={() => setFilter('all')}
              >
                <span className="text">News For You</span>
              </button>
              {availableCategories.map(category => (
                <button
                  key={category}
                  className={`sidebar-item ${filter === category ? 'active' : ''}`}
                  onClick={() => setFilter(category)}
                >
                  <span className="text">{category}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="sidebar-section" data-guide="platforms">
            <div className="sidebar-section-header">
              <h3>Trusted Platforms</h3>
              <button
                className="manage-platforms-btn"
                onClick={() => setIsManagingPlatforms((prev) => !prev)}
                title={isManagingPlatforms ? 'Done managing' : 'Manage platforms'}
              >
                {isManagingPlatforms ? 'Done' : 'Manage'}
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
                          {following ? 'Following' : 'Follow'}
                        </button>
                      </>
                    ) : following ? (
                      <span className="following-item">
                        {platform.name}
                      </span>
                    ) : null}
                  </div>
                );
              })}

              {!isManagingPlatforms && platforms.every((p) => !isFollowing(p.id)) && (
                <p className="no-platforms-message">
                  You're not following any platforms yet. Click "Manage" to follow some.
                </p>
              )}
            </div>

            {isManagingPlatforms && (
              <button
                type="button"
                className="reset-platforms-btn"
                onClick={handleResetPlatforms}
              >
                Reset to Defaults
              </button>
            )}
          </div>
        </div>

        <div className="main-content">
          <SuggestionPanel onSaved={handleInterestsSaved} />

          <div className="feed-toolbar" data-guide="toolbar">
            <div className="refresh-controls">
              <div className="refresh-button-group">
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
                    <><RefreshIcon size={18} /> Refresh News</>
                  )}
                </button>
                
              </div>
              
              {refreshing && <p role="status">Collecting and analyzing articles. This may take a few minutes.</p>}
            </div>
            {filter === 'all' && !searchActive && (
              <label className="feed-sort">
                <span>Order</span>
                <select value={sortMode} onChange={(e) => changeSort(e.target.value)} aria-label="Order of News For You">
                  <option value="foryou">Recommended for you</option>
                  <option value="newest">Newest first</option>
                </select>
              </label>
            )}
          </div>
          {searchActive && (
            <p className="feed-status" role="status">
              {searching ? 'Searching all saved articles...'
                : serverMatches
                  ? (serverTotal > displayArticles.length
                    ? `Showing the newest ${displayArticles.length} of ${serverTotal} results`
                    : `${displayArticles.length} result${displayArticles.length === 1 ? '' : 's'} from all saved articles`)
                  : 'Showing matches from the latest articles'}
            </p>
          )}
          {personalOn && !personalised && !loading && (
            <p className="feed-status">Read or bookmark a few stories and News For You will be ordered for you.</p>
          )}
          {error && <div className="feed-error">{error}</div>}

          {loading ? (
            <div className="feed-loading">
                            <p>Fetching the latest news...</p>
            </div>
          ) : (
            <div className="articles-grid" data-guide="articles">
              {displayArticles.length > 0 ? (
                displayArticles.map(article => (
                  <ArticleCard key={article.id} article={article} />
                ))
              ) : (
                <div className="no-results">
                                    <h3>No articles found</h3>
                  <p>{filter === 'all' && selectedTopics?.length && !searchQuery.trim()
                    ? 'No recent articles match your interests yet. Try adding more interests, or hit "Refresh News" to fetch the latest.'
                    : 'Try adjusting your search or filters, or hit "Refresh News" to fetch the latest.'}</p>
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
