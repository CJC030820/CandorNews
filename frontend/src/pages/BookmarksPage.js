import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useBookmarks } from '../context/BookmarkContext';
import BackToTopButton from '../components/BackToTopButton';
import './BookmarksPage.css';

const BookmarksPage = () => {
  const navigate = useNavigate();
  const { bookmarks, removeBookmark } = useBookmarks();

  const handleOpenArticle = (article) => {
    navigate(`/article/${article.id}`, { state: { article } });
  };

  const handleRemove = (e, articleId) => {
    e.stopPropagation();
    removeBookmark(articleId);
  };

  return (
    <div className="bookmarks-page">
      <BackToTopButton />
      <div className="bookmarks-page-wrapper">
        <button className="back-btn" onClick={() => navigate('/feed')}>
          <span className="back-btn-icon">←</span>
          <span className="back-btn-label">Back to Main Page</span>
        </button>

        <div className="bookmarks-header">
          <h1>📑 My Bookmarks</h1>
          {bookmarks.length > 0 && (
            <p className="bookmarks-count">{bookmarks.length} article{bookmarks.length !== 1 ? 's' : ''} saved</p>
          )}
        </div>

        <div className="bookmarks-content">
          {bookmarks.length > 0 ? (
            <div className="bookmarks-grid">
              {bookmarks.map(article => (
                <div
                  key={article.id}
                  className="bookmark-item"
                  onClick={() => handleOpenArticle(article)}
                >
                  <div className="bookmark-image">
                    <img src={article.image} alt={article.title} />
                    {article.trustScore !== undefined && (
                      <span className="bookmark-trust-score">{article.trustScore}% Trust</span>
                    )}
                  </div>
                  <h3>{article.title}</h3>
                  <p>{article.source} • {article.date}</p>
                  <button
                    className="remove-btn"
                    onClick={(e) => handleRemove(e, article.id)}
                  >
                    🗑️ Remove
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <span className="empty-icon">📭</span>
              <p>No bookmarks yet. Start bookmarking articles!</p>
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

export default BookmarksPage;
