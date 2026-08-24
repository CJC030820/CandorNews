import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { BookmarkProvider } from './context/BookmarkContext';
import { ReadArticlesProvider } from './context/ReadArticlesContext';
import { TrustedPlatformsProvider } from './context/TrustedPlatformsContext';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import TopicSelectionPage from './pages/TopicSelectionPage';
import FeedPage from './pages/FeedPage';
import ArticleDetailPage from './pages/ArticleDetailPage';
import BookmarksPage from './pages/BookmarksPage';
import HistoryPage from './pages/HistoryPage';
import ProfilePage from './pages/ProfilePage';
import NavBar from './components/NavBar';

function AppRoutes({ searchQuery, onSearchChange }) {
  const { user, topicsCompleted, loading } = useAuth();

  useEffect(() => {
    console.log('AppRoutes state changed:', {
      user: user?.email,
      topicsCompleted,
      loading
    });
  }, [user, topicsCompleted, loading]);

  // Show loading screen while checking auth
  if (loading) {
    return (
      <div className="app-loading">
        <div className="app-loading-spinner" aria-label="Loading" />
        <p>Loading…</p>
      </div>
    );
  }

  // Redirect logic based on user state
  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  // If user is logged in but hasn't completed topic selection
  if (!topicsCompleted) {
    return (
      <Routes>
        <Route path="/topic-selection" element={<TopicSelectionPage />} />
        <Route path="*" element={<Navigate to="/topic-selection" replace />} />
      </Routes>
    );
  }

  // If user is logged in and has completed topic selection, allow full app access
  return (
    <Routes>
      <Route
        path="/feed"
        element={<FeedPage searchQuery={searchQuery} onSearchChange={onSearchChange} />}
      />
      <Route path="/article/:id" element={<ArticleDetailPage />} />
      <Route path="/bookmarks" element={<BookmarksPage />} />
      <Route path="/history" element={<HistoryPage />} />
      <Route path="/profile" element={<ProfilePage />} />
      <Route path="/" element={<Navigate to="/feed" replace />} />
      <Route path="*" element={<Navigate to="/feed" replace />} />
    </Routes>
  );
}

function AppShell() {
  const [searchQuery, setSearchQuery] = useState('');
  const { user } = useAuth();

  return (
    <div className="App">
      {user && (
        <NavBar
          searchQuery={searchQuery}
          onSearchChange={(value) => setSearchQuery(value)}
        />
      )}
      <AppRoutes searchQuery={searchQuery} onSearchChange={setSearchQuery} />
    </div>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BookmarkProvider>
          <ReadArticlesProvider>
            <TrustedPlatformsProvider>
              <Router>
                <AppShell />
              </Router>
            </TrustedPlatformsProvider>
          </ReadArticlesProvider>
        </BookmarkProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
