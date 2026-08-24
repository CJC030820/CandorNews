import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const ReadArticlesContext = createContext();

const STORAGE_KEY = 'readArticleHistory';

const getHistoryFromStorage = () => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch (e) {
    console.error('Error parsing read history from localStorage:', e);
    return [];
  }
};

export const ReadArticlesProvider = ({ children }) => {
  // Each entry: { ...articleFields, id, readAt: <ISO timestamp> }
  // Sorted most-recently-read first.
  const [history, setHistory] = useState(getHistoryFromStorage);

  // Persist to localStorage whenever history changes
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
  }, [history]);

  // Keep history in sync in real time across browser tabs/windows: if another
  // tab marks an article as read, this tab's History page (and any read
  // badges) update immediately without needing a manual refresh.
  useEffect(() => {
    const handleStorageChange = (e) => {
      if (e.key === STORAGE_KEY) {
        setHistory(getHistoryFromStorage());
      }
    };
    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  const isRead = useCallback((articleId) => {
    if (articleId === undefined || articleId === null) return false;
    return history.some((entry) => String(entry.id) === String(articleId));
  }, [history]);

  // Records (or re-records) an article as read. Every time the user views
  // the article, this bumps it to the top of the history with a fresh
  // timestamp, so History reflects real-time viewing activity.
  const markAsRead = useCallback((article) => {
    if (!article || article.id === undefined || article.id === null) return;
    setHistory((prev) => {
      const withoutThis = prev.filter((entry) => String(entry.id) !== String(article.id));
      const entry = { ...article, readAt: new Date().toISOString() };
      return [entry, ...withoutThis];
    });
  }, []);

  const removeFromHistory = useCallback((articleId) => {
    setHistory((prev) => prev.filter((entry) => String(entry.id) !== String(articleId)));
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
  }, []);

  const value = {
    history,
    readArticleIds: history.map((entry) => entry.id),
    readCount: history.length,
    isRead,
    markAsRead,
    removeFromHistory,
    clearHistory
  };

  return (
    <ReadArticlesContext.Provider value={value}>
      {children}
    </ReadArticlesContext.Provider>
  );
};

export const useReadArticles = () => {
  const context = useContext(ReadArticlesContext);
  if (!context) {
    throw new Error('useReadArticles must be used within a ReadArticlesProvider');
  }
  return context;
};
