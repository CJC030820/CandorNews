import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';

const ArticleDetailPage = () => {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [article, setArticle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchArticle = async () => {
      if (!user) {
        navigate('/login');
        return;
      }
      setLoading(true);
      try {
        const response = await axios.get(`/api/articles/${id}`, {
          headers: { Authorization: `Bearer ${user.token}` }
        });
        setArticle(response.data);
        // Record a view/click interaction
        await axios.post(
          `/api/interactions/click/${id}`,
          {},
          {
            headers: { Authorization: `Bearer ${user.token}` }
          }
        );
      } catch (err) {
        console.error('Error fetching article:', err);
        setError('Failed to load article');
      } finally {
        setLoading(false);
      }
    };

    fetchArticle();
  }, [id, user]);

  if (loading) {
    return <div className="article-detail-page">Loading article...</div>;
  }

  if (error) {
    return <div className="article-detail-page"><p className="error">{error}</p></div>;
  }

  if (!article) {
    return <div className="article-detail-page"><p>Article not found</p></div>;
  }

  const formatDate = (dateString) => {
    if (!dateString) return '';
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString(undefined, options);
  };

  return (
    <div className="article-detail-page">
      <div className="article-header">
        <h1>{article.title}</h1>
        <div className="article-meta">
          <span>{article.source}</span>
          <span>|</span>
          <span>{formatDate(article.published_date)}</span>
          <span>|</span>
          <span>{article.topic}</span>
        </div>
      </div>
      <div className="article-content">
        <p className="article-summary">{article.summary}</p>
        {article.content_excerpt && (
          <div className="article-excerpt">
            <p>{article.content_excerpt}</p>
          </div>
        )}
      </div>
      <div className="article-analysis">
        <div className="analysis-item">
          <h3>Sentiment</h3>
          <p className={`sentiment-tag ${article.sentiment.toLowerCase()}`}>
            {article.sentiment}
          </p>
        </div>
        <div className="analysis-item">
          <h3>Trust Score</h3>
          <p>
            {article.trust_score}/100
            <span className="trust-label">({article.trust_label})</span>
          </p>
          <p className="trust-explanation">{article.trust_explanation}</p>
        </div>
        <div className="analysis-item">
          <h3>Recommendation Reason</h3>
          <p>{article.recommendation_explanation || 'Recommended based on your interests and article quality.'}</p>
        </div>
      </div>
      <div className="article-actions">
        <button
          onClick={async () => {
            if (!user) {
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
          }}
        >
          🔖 Bookmark
        </button>
        <a href={article.url} target="_blank" rel="noopener noreferrer">
          Read Original Article
        </a>
      </div>
    </div>
  );
};

export default ArticleDetailPage;