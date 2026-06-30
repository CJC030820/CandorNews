import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import ArticleCard from '../components/ArticleCard';
import axios from 'axios';

const BookmarksPage = () => {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchBookmarks = async () => {
      if (!user) {
        navigate('/login');
        return;
      }
      setLoading(true);
      try {
        const response = await axios.get('/api/bookmarks', {
          headers: { Authorization: `Bearer ${user.token}` }
        });
        setArticles(response.data);
      } catch (err) {
        console.error('Error fetching bookmarks:', err);
        setError('Failed to load bookmarks');
      } finally {
        setLoading(false);
      }
    };

    fetchBookmarks();
  }, [user]);

  if (loading) {
    return <div className="bookmarks-page">Loading bookmarks...</div>;
  }

  if (error) {
    return <div className="bookmarks-page"><p className="error">{error}</p></div>;
  }

  return (
    <div className="bookmarks-page">
      <h2>Bookmarked Articles</h2>
      {articles.length === 0 ? (
        <p>You haven't bookmarked any articles yet.</p>
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

export default BookmarksPage;