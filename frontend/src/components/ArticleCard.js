import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const ArticleCard = ({ article, navigate }) => {
  const { user } = useAuth();
  const navigateToArticle = () => {
    navigate(`/article/${article.id}`);
  };

  const handleBookmark = async (e) => {
    e.stopPropagation();
    if (!user) {
      // Redirect to login
      navigate('/login');
      return;
    }
    try {
      const response = await axios.post(
        `/api/bookmarks/${article.id}`,
        {},
        {
          headers: { Authorization: `Bearer ${user.token}` }
        }
      );
      alert(response.data.message);
    } catch (err) {
      console.error('Error bookmarking:', err);
      alert('Failed to bookmark article');
    }
  };

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return '';
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString(undefined, options);
  };

  return (
    <div className="article-card" onClick={navigateToArticle}>
      <div className="article-content">
        <h3>{article.title}</h3>
        <div className="article-meta">
          <span className="article-source">{article.source}</span>
          <span className="article-date">{formatDate(article.published_date)}</span>
          <span className="article-topic">{article.topic}</span>
        </div>
        <p className="article-summary">{article.summary}</p>
        <div className="article-tags">
          <span className={`sentiment ${article.sentiment.toLowerCase()}`}>
            {article.sentiment}
          </span>
          <span className="trust-score">
            Trust: {article.trust_score} ({article.trust_label || ''})
          </span>
        </div>
        <button className="bookmark-btn" onClick={handleBookmark}>
          🔖
        </button>
      </div>
    </div>
  );
};

export default ArticleCard;