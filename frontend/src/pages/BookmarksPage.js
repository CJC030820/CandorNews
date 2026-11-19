import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import PageWrapper from '../components/PageWrapper';
import { useBookmarks } from '../context/BookmarkContext';
import BackToTopButton from '../components/BackToTopButton';
import './BookmarksPage.css';
import ArticleImage from '../components/ArticleImage';
import { BackIcon, BookmarkIcon } from '../components/Icons';
import ArticleFilters from '../components/ArticleFilters';
import { EMPTY_FILTERS, bookmarkTime, filterBookmarks, historyCategories } from '../utils/historyFilter';

// "Saved 19 Nov 2026" (older bookmarks without a saved time show the publish date)
const bookmarkDateLabel = (article) => {
  const when = bookmarkTime(article);
  const d = when ? new Date(when) : null;
  if (!d || Number.isNaN(d.getTime())) return article.date || '';
  const text = d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
  return article.savedAt ? `Saved ${text}` : `Published ${text}`;
};

const BookmarksPage = () => {
  const navigate = useNavigate();
  const { bookmarks, removeBookmark } = useBookmarks();
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const categories = useMemo(() => historyCategories(bookmarks), [bookmarks]);
  const visible = useMemo(() => filterBookmarks(bookmarks, filters), [bookmarks, filters]);

  const handleOpenArticle = (article) => {
    navigate(`/article/${article.id}`, { state: { article } });
  };

  const handleRemove = (e, articleId) => {
    e.stopPropagation();
    removeBookmark(articleId);
  };

  return (
    <PageWrapper>
    <div className="bookmarks-page">
      <BackToTopButton />
      <div className="bookmarks-page-wrapper">
        <button className="back-btn" onClick={() => navigate('/feed')}>
                    <BackIcon size={20} />
                    <span className="back-btn-label">Back to Main Page</span>
        </button>

        <div className="bookmarks-header">
          <h1><BookmarkIcon filled size={28} /> My Bookmarks</h1>
          {bookmarks.length > 0 && (
            <p className="bookmarks-count">{bookmarks.length} article{bookmarks.length !== 1 ? 's' : ''} saved</p>
          )}
        </div>

        {bookmarks.length > 0 && (
          <ArticleFilters
            value={filters}
            onChange={setFilters}
            categories={categories}
            total={bookmarks.length}
            shown={visible.length}
            timeLabel="Time saved"
            label="Filter bookmarks"
          />
        )}

        <div className="bookmarks-content">
          {bookmarks.length > 0 && visible.length === 0 ? (
            <div className="empty-state">
              <p>No bookmarks match these filters.</p>
              <button className="browse-btn" onClick={() => setFilters(EMPTY_FILTERS)}>Clear filters</button>
            </div>
          ) : bookmarks.length > 0 ? (
            <div className="bookmarks-grid">
              {visible.map(article => (
                <div
                  key={article.id}
                  className="bookmark-item"
                  onClick={() => handleOpenArticle(article)}
                >
                  <div className="bookmark-image">
                    <ArticleImage article={article} />
                    {article.trustScore !== undefined && (
                      <span className="bookmark-trust-score">{article.trustScore}% Trust</span>
                    )}
                  </div>
                  <h3>{article.title}</h3>
                  <p>{article.source} • {bookmarkDateLabel(article)}</p>
                  <button
                    className="remove-btn"
                    onClick={(e) => handleRemove(e, article.id)}
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <span className="empty-icon"><BookmarkIcon size={56} /></span>
              <p>No bookmarks yet. Start bookmarking articles!</p>
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

export default BookmarksPage;
