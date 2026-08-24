import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { useBookmarks } from '../context/BookmarkContext';
import { useReadArticles } from '../context/ReadArticlesContext';
import ShareMenu from '../components/ShareMenu';
import './ArticleDetailPage.css';

const toneBadgeClass = (toneLabel) => {
  if (!toneLabel) return '';
  if (toneLabel.includes('Neutral')) return 'tone-neutral';
  if (toneLabel.includes('Mildly')) return 'tone-mild';
  return 'tone-charged';
};

const toneIcon = (toneLabel) => {
  if (!toneLabel) return '';
  if (toneLabel.includes('Neutral')) return '⚖️';
  if (toneLabel.includes('Mildly')) return '🗣️';
  return '🔥';
};

const ArticleDetailPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { id } = useParams();
  const { isBookmarked, toggleBookmark, bookmarks } = useBookmarks();
  const { markAsRead } = useReadArticles();
  const [imageError, setImageError] = useState(false);
  const [isExiting, setIsExiting] = useState(false);

  // Prefer article passed via navigation state; fall back to a bookmarked
  // article with matching id (e.g. after a page refresh).
  const article =
    location.state?.article ||
    bookmarks.find((a) => String(a.id) === String(id)) ||
    {};

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

  const handleBookmarkClick = () => {
    if (article.id !== undefined) {
      toggleBookmark(article);
    }
  };

  const handleBack = () => {
    setIsExiting(true);
    setTimeout(() => {
      navigate(-1);
    }, 300);
  };

  return (
    <div className={`article-detail-page ${isExiting ? 'fade-out' : 'fade-in'}`}>
      <div className="article-detail-wrapper">
        <button className="back-button" onClick={handleBack}>
          <span className="back-button-icon">←</span>
          <span className="back-button-label">Back</span>
        </button>
        <article className="article-detail">
          <h1>{article.title}</h1>
          <div className="article-meta">
            <span>{article.source}</span>
            <span>{article.date}</span>
            <span className="trust-score-detail">{article.trustScore}% Trust</span>
          </div>
          {article.toneLabel && (
            <div className="tone-label-row">
              <span className={`tone-badge ${toneBadgeClass(article.toneLabel)}`}>
                {toneIcon(article.toneLabel)} {article.toneLabel}
              </span>
            </div>
          )}
          {(article.categories && article.categories.length > 0) && (
            <div className="article-categories-detail">
              {article.categories.slice(0, 3).map((cat) => (
                <span key={cat} className="category-chip-detail">{cat}</span>
              ))}
            </div>
          )}
          {article.image && !imageError ? (
            <img
              src={article.image}
              alt={article.title}
              className="article-image-detail"
              onError={() => setImageError(true)}
            />
          ) : (
            <div className="article-image-detail article-image-placeholder">
              <span className="article-image-placeholder-icon">📰</span>
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
              >
                🔗 Read Original Article on {article.source || 'Source Site'}
              </a>
            </div>
          )}

          <div className="article-demo-notice">
            <p>This is a detailed article view. In a real application, this would fetch full content from the backend API.</p>
          </div>

          <div className="article-actions">
            <button
              className={`bookmark-btn ${bookmarked ? 'active' : ''}`}
              onClick={handleBookmarkClick}
            >
              {bookmarked ? '🔖 Bookmarked' : '📑 Bookmark'}
            </button>
            {article.id !== undefined && <ShareMenu article={article} variant="button" />}
          </div>
        </article>
      </div>
    </div>
  );
};

export default ArticleDetailPage;
