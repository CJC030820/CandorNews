import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { useBookmarks } from '../context/BookmarkContext';
import { useReadArticles } from '../context/ReadArticlesContext';
import { useAuth } from '../context/AuthContext';
import ArticleAnalysis from '../components/ArticleAnalysis';
import StoryTimeline from '../components/StoryTimeline';
import ShareMenu from '../components/ShareMenu';
import { useArticleImage } from '../utils/articleImage';
import { ImagePlaceholder } from '../components/ArticleImage';
import './ArticleDetailPage.css';
import { BackIcon, BookmarkIcon } from '../components/Icons';

const ArticleDetailPage = () => {
  const location = useLocation();
  const { getArticle } = useAuth();
  const [fetched, setFetched] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { id } = useParams();
  const { isBookmarked, toggleBookmark, bookmarks } = useBookmarks();
  const { markAsRead } = useReadArticles();
  const [isExiting, setIsExiting] = useState(false);

  // Prefer article passed via navigation state; fall back to a bookmarked
  // article with matching id (e.g. after a page refresh).
  const article =
    (fetched?.id === id ? fetched : null) ||
    location.state?.article ||
    bookmarks.find((a) => String(a.id) === String(id)) ||
    {};
  const detailImage = useArticleImage(article);

  useEffect(() => {
    let active = true;
    setLoading(true); setLoadError(''); setFetched(null);
    getArticle(id).then(data => { if (active) setFetched({...data, date:new Date(data.date).toLocaleString()}); })
      .catch(error => { if (active) setLoadError(error.response?.status === 404 ? 'Article not found.' : 'Could not update this article. Please retry.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id, getArticle]);

  const bookmarked = article.id !== undefined && isBookmarked(article.id);

  // Record this article as "read" as soon as the user opens its detail page.
  // Runs every time the article is viewed (including re-visits), so History
  // updates in real time and the most recently viewed article stays on top.
  useEffect(() => {
    // Scroll to top when entering article detail page
    window.scrollTo(0, 0);
    if (article.id !== undefined) {
      markAsRead(article);
    }
    // eslint-disable-next-line
  }, [article.id]);

  // "Compare N versions" on a feed card opens the page at the comparison.
  useEffect(() => {
    const section = location.hash.slice(1);
    if (!loading && (section === 'compare' || section === 'timeline')) {
      document.getElementById(section)?.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
    }
  }, [loading, location.hash, id]);

  const handleBookmarkClick = () => {
    if (article.id !== undefined) {
      toggleBookmark(article);
    }
  };

  // Opened from inside the app (feed, bookmarks, history pass the article in
  // navigation state): go back to that page. Opened from a shared or email
  // link: there is no earlier CandorNews page in this tab, so go to the feed.
  const openedInApp = Boolean(location.state?.article);
  const handleBack = () => {
    setIsExiting(true);
    setTimeout(() => {
      if (openedInApp) navigate(-1);
      else navigate('/feed', { replace: true });
    }, 300);
  };

  if (!article.id) return <main className="article-detail-page"><p role="status">{loading ? 'Loading article…' : loadError}</p><button onClick={() => navigate('/feed')}>Back to news</button></main>;
  return (
    <div className="article-detail-page">
      <div className="article-detail-wrapper">
        <button className="back-button" onClick={handleBack}>
                    <BackIcon size={20} />
                    <span className="back-button-label">Back</span>
        </button>
        {/* Bookmark and share sit in the top row, so they are reachable without scrolling. */}
        <div className="article-actions article-top-actions">
          <button
            className={`bookmark-btn ${bookmarked ? 'active' : ''}`}
            onClick={handleBookmarkClick}
            aria-pressed={bookmarked}
          >
            <BookmarkIcon filled={bookmarked} size={18} /> {bookmarked ? 'Bookmarked' : 'Bookmark'}
          </button>
          {article.id !== undefined && <ShareMenu article={article} variant="button" />}
        </div>
        <article className="article-detail">
          <h1>{article.title}</h1>
          {loadError && <p role="alert">{loadError} Showing the saved copy.</p>}
          <div className="article-meta">
            <span>{article.source}</span>
            <span>{article.date}</span>
            <span className="trust-score-detail">{article.trustScore == null ? 'Analysis pending' : `${article.trustScore}/100 trust`}</span>
          </div>
          {(article.categories && article.categories.length > 0) && (
            <div className="article-categories-detail">
              {article.categories.slice(0, 3).map((cat) => (
                <span key={cat} className="category-chip-detail">{cat}</span>
              ))}
            </div>
          )}
          {detailImage.src ? (
            <img
              src={detailImage.src}
              alt={article.title}
              className="article-image-detail"
              ref={detailImage.ref}
              onError={detailImage.onError}
              onLoad={detailImage.onLoad}
            />
          ) : (
            <div className="article-image-detail article-image-placeholder">
              <ImagePlaceholder article={article} />
            </div>
          )}
          <div className="article-body">
            <p>{article.description}</p>
          </div>

          {article.url && (
            <div className="article-source-link">
              <a
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="original-source-btn"
                aria-label={`Read Original Article on ${article.source || 'the publisher\'s site'} (opens in a new tab)`}
              >
                Read Original Article
              </a>
            </div>
          )}

          <StoryTimeline timeline={article.timeline} />
          <ArticleAnalysis article={article} loading={loading} />

        </article>
      </div>
    </div>
  );
};

export default ArticleDetailPage;
