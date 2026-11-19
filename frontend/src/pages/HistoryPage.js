import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import PageWrapper from '../components/PageWrapper';
import { useReadArticles } from '../context/ReadArticlesContext';
import BackToTopButton from '../components/BackToTopButton';
import './HistoryPage.css';
import ArticleImage from '../components/ArticleImage';
import { BackIcon, HistoryIcon } from '../components/Icons';
import ArticleFilters from '../components/ArticleFilters';
import { EMPTY_FILTERS, filterHistory, historyCategories } from '../utils/historyFilter';

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
  const [filters, setFilters] = useState(EMPTY_FILTERS);

  const categories = useMemo(() => historyCategories(history), [history]);
  const visible = useMemo(() => filterHistory(history, filters), [history, filters]);
  const clearFilters = () => setFilters(EMPTY_FILTERS);

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
    <PageWrapper>
    <div className="history-page">
      <BackToTopButton />
      <div className="history-page-wrapper">
        <button className="back-btn" onClick={() => navigate('/feed')}>
                    <BackIcon size={20} />
                    <span className="back-btn-label">Back to Main Page</span>
        </button>

        <div className="history-header">
          <div className="history-title-row">
            <div>
              <h1><HistoryIcon size={28} /> Reading History</h1>
              {history.length > 0 && (
                <p className="history-count">
                  {history.length} article{history.length !== 1 ? 's' : ''} read
                </p>
              )}
            </div>
            {history.length > 0 && (
              <button className="clear-history-btn" onClick={handleClearAll}>
                Clear All
              </button>
            )}
          </div>
        </div>

        {history.length > 0 && (
          <ArticleFilters
            value={filters}
            onChange={setFilters}
            categories={categories}
            total={history.length}
            shown={visible.length}
            timeLabel="Time viewed"
            label="Filter reading history"
          />
        )}

        <div className="history-content">
          {history.length > 0 && visible.length === 0 ? (
            <div className="empty-state">
              <p>No articles in your history match these filters.</p>
              <button className="browse-btn" onClick={clearFilters}>Clear filters</button>
            </div>
          ) : history.length > 0 ? (
            <div className="history-list">
              {visible.map((article) => (
                <div
                  key={article.id}
                  className="history-item"
                  onClick={() => handleOpenArticle(article)}
                >
                  <div className="history-image">
                    <ArticleImage article={article} compact />
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
                      Viewed {formatReadAt(article.readAt)}
                    </p>
                    <p className="history-read-at-exact">{formatExactDateTime(article.readAt)}</p>
                  </div>
                  <button
                    className="history-remove-btn"
                    onClick={(e) => handleRemove(e, article.id)}
                    title="Remove from history"
                    aria-label="Remove from history"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <span className="empty-icon"><HistoryIcon size={56} /></span>
              <p>No reading history yet. Articles you open will show up here.</p>
              <button className="browse-btn" onClick={() => navigate('/feed')}>
                Browse News Feed
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
    </PageWrapper>
  );
};

export default HistoryPage;
