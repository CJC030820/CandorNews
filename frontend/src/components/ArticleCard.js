import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useBookmarks } from '../context/BookmarkContext';
import { useReadArticles } from '../context/ReadArticlesContext';
import ShareMenu from './ShareMenu';
import './ArticleCard.css';

const ArticleCard = ({ article }) => {
  const navigate = useNavigate();
  const [imageSource, setImageSource] = useState(article.image);
  const [imageError, setImageError] = useState(!article.image);
  const [showExpandedSummary, setShowExpandedSummary] = useState(false);
  const { isBookmarked, toggleBookmark } = useBookmarks();
  const { isRead } = useReadArticles();
  const bookmarked = isBookmarked(article.id);
  const read = isRead(article.id);

  const handleClick = () => {
    // Save current scroll position before navigating
    sessionStorage.setItem('feedScrollPosition', window.scrollY.toString());
    navigate(`/article/${article.id}`, { state: { article } });
  };

  const handleImageError = () => {
    // Try fallback image if available
    if (article.fallbackImage && imageSource === article.image) {
      setImageSource(article.fallbackImage);
    } else {
      // If fallback also fails, show placeholder
      setImageError(true);
    }
  };

  const handleBookmarkClick = (e) => {
    e.stopPropagation();
    toggleBookmark(article);
  };

  const handleExpandClick = (e) => {
    e.stopPropagation();
    setShowExpandedSummary(true);
  };

  const handleCloseExpanded = (e) => {
    e.stopPropagation();
    setShowExpandedSummary(false);
  };

  return (
    <div className="article-card" onClick={handleClick}>
      <div className="article-image">
        {!imageError ? (
          <img 
            src={imageSource} 
            alt={article.title}
            onError={handleImageError}
            loading="lazy"
          />
        ) : (
          <div className="image-placeholder">
            <span className="placeholder-icon">📰</span>
          </div>
        )}
        <button
          className={`bookmark-toggle ${bookmarked ? 'active' : ''}`}
          onClick={handleBookmarkClick}
          title={bookmarked ? 'Remove bookmark' : 'Add bookmark'}
          aria-label={bookmarked ? 'Remove bookmark' : 'Add bookmark'}
        >
          <span className="bookmark-toggle-icon">{bookmarked ? '🔖' : '📑'}</span>
        </button>
        <div className="card-share-wrapper" onClick={(e) => e.stopPropagation()}>
          <ShareMenu article={article} variant="icon" />
        </div>
        <span className="trust-score">{article.trustScore}% Trust</span>
        <div className="category-badges">
          {(article.categories && article.categories.length > 0 ? article.categories : [article.category])
            .filter(Boolean)
            .slice(0, 3)
            .map((cat) => (
              <span key={cat} className="category-badge">{cat}</span>
            ))}
        </div>
        {read && <span className="read-badge">✓ Read</span>}
      </div>
      <div className="article-content">
        <h3 className="article-title">{article.title}</h3>
        <p className="article-meta">
          <span className="source">{article.source}</span>
          <span className="date">{article.date}</span>
        </p>
        <p className="article-description">{article.description}</p>
        <div className="article-actions">
          {article.content && article.content.length > article.description?.length && (
            <button 
              className="expand-summary" 
              onClick={handleExpandClick}
              title="View full summary"
            >
              📖 Expand
            </button>
          )}
          <button className="read-more">Read More →</button>
        </div>
      </div>

      {showExpandedSummary && (
        <div className="expanded-summary-modal" onClick={handleCloseExpanded}>
          <div className="expanded-summary-content" onClick={(e) => e.stopPropagation()}>
            <div className="expanded-summary-header">
              <h2 className="expanded-summary-title">{article.title}</h2>
              <button 
                className="expanded-summary-close" 
                onClick={handleCloseExpanded}
                title="Close"
              >
                ✕
              </button>
            </div>
            <div className="expanded-summary-meta">
              <span className="expanded-source">{article.source}</span>
              <span className="expanded-date">{article.date}</span>
              <span className="expanded-trust">{article.trustScore}% Trust</span>
            </div>
            <div className="expanded-summary-body">
              {article.content || article.description}
            </div>
            <div className="expanded-summary-footer">
              <button className="expanded-read-more" onClick={handleClick}>
                🔗 Read Full Article →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ArticleCard;
