import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useReadArticles } from '../context/ReadArticlesContext';
import BackToTopButton from '../components/BackToTopButton';
import './HistoryPage.css';

const formatReadAt = (isoString) => {
  if (!isoString) return '';
  const readDate = new Date(isoString);
  if (Number.isNaN(readDate.getTime())) return '';

  const now = new Date();
  const diffMs = now - readDate;
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} min${diffMins !== 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
  return readDate.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
};

// Full, exact date + time the article was viewed, e.g. "Aug 8, 2026, 11:06 PM"
const formatExactDateTime = (isoString) => {
  if (!isoString) return '';
  const readDate = new Date(isoString);
  if (Number.isNaN(readDate.getTime())) return '';

  const datePart = readDate.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
  const timePart = readDate.toLocaleTimeString(undefined, {
    hour: 'numeric',
    minute: '2-digit'
  });
  return `${datePart}, ${timePart}`;
};

const HistoryPage = () => {
  const navigate = useNavigate();
  const { history, removeFromHistory, clearHistory } = useReadArticles();

  const handleOpenArticle = (article) => {
    navigate(`/article/${article.id}`, { state: { article } });
  };

  const handleRemove = (e, articleId) => {
    e.stopPropagation();
    removeFromHistory(articleId);
  };

  const handleClearAll = () => {
    if (window.confirm('Clear your entire reading history?')) {
      clearHistory();
    }
  };

  return (
    <div className="history-page">
      <BackToTopButton />
      <div className="history-page-wrapper">
        <button className="back-btn" onClick={() => navigate('/feed')}>
          <span className="back-btn-icon">←</span>
          <span className="back-btn-label">Back to Main Page</span>
        </button>

        <div className="history-header">
          <div className="history-title-row">
            <div>
              <h1>🕘 Reading History</h1>
              {history.length > 0 && (
                <p className="history-count">
                  {history.length} article{history.length !== 1 ? 's' : ''} read
                </p>
              )}
            </div>
            {history.length > 0 && (
              <button className="clear-history-btn" onClick={handleClearAll}>
                🗑️ Clear All
              </button>
            )}
          </div>
        </div>

        <div className="history-content">
          {history.length > 0 ? (
            <div className="history-list">
              {history.map((article) => (
                <div
                  key={article.id}
                  className="history-item"
                  onClick={() => handleOpenArticle(article)}
                >
                  <div className="history-image">
                    <img src={article.image} alt={article.title} />
                  </div>
                  <div className="history-details">
                    <h3>{article.title}</h3>
                    <p className="history-meta">
                      <span>{article.source}</span>
                      {article.trustScore !== undefined && (
                        <span className="history-trust-score">{article.trustScore}% Trust</span>
                      )}
                    </p>
                    <p className="history-read-at" title={formatExactDateTime(article.readAt)}>
                      👁️ Viewed {formatReadAt(article.readAt)}
                    </p>
                    <p className="history-read-at-exact">📅 {formatExactDateTime(article.readAt)}</p>
                  </div>
                  <button
                    className="history-remove-btn"
                    onClick={(e) => handleRemove(e, article.id)}
                    title="Remove from history"
                    aria-label="Remove from history"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <span className="empty-icon">🕘</span>
              <p>No reading history yet. Articles you open will show up here.</p>
              <button className="browse-btn" onClick={() => navigate('/feed')}>
                Browse News Feed
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default HistoryPage;
