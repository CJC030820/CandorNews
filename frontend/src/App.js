import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import TopicSelectionPage from './pages/TopicSelectionPage';
import FeedPage from './pages/FeedPage';
import ArticleDetailPage from './pages/ArticleDetailPage';
import BookmarksPage from './pages/BookmarksPage';
import ProfilePage from './pages/ProfilePage';
import { AuthProvider } from './context/AuthContext';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/topic-selection" element={<TopicSelectionPage />} />
          <Route path="/feed" element={<FeedPage />} />
          <Route path="/article/:id" element={<ArticleDetailPage />} />
          <Route path="/bookmarks" element={<BookmarksPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
