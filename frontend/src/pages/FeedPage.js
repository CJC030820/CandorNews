import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { useLDFlag } from 'ldclient-react';
import ArticleCard from '../components/ArticleCard';
import axios from 'axios';

const FeedPage = () => {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { user } = useAuth();
  const navigate = useNavigate();
  const showNewFeature = useLDFlag('new_feature', false);

  useEffect(() => {
    const fetchArticles = async () => {
      if (!user) {
        navigate('/login');
        return;
      }
      setLoading(true);
      try {
        const response = await axios.get('/api/articles/feed', {
          headers: { Authorization: `Bearer ${user.token}` }
        });
        setArticles(response.data);
      } catch (err) {
        console.error('Error fetching articles:', err);
        setError('Failed to load news feed');
      } finally {
        setLoading(false);
      }
    };

    fetchArticles();
  }, [user]);

  if (loading) {
    return <div className="feed-page">Loading news...</div>;
  }

  if (error) {
    return <div className="feed-page"><p className="error">{error}</p></div>;
  }

  return (
    <div className="feed-page">
      <h2>Personalized News Feed</h2>
      {showNewFeature && <p>New feature is enabled! This is a feature flag example.</p>}
      {articles.length === 0 ? (
        <p>No articles available. Please check back later.</p>
      ) : (
        <div className="articles-grid">
          {articles.map(article => (
            <ArticleCard key={article.id} article={article} navigate={navigate} />
          ))}
        </div>
      )}
    </div>
  );
};

export default FeedPage;