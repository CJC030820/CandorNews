import React, { createContext, useContext, useCallback } from 'react';
import { useAccountStorage } from '../hooks/useAccountStorage';

const ReadArticlesContext = createContext();

const EMPTY = [];

export const ReadArticlesProvider = ({ children }) => {
  const [history, setHistory] = useAccountStorage('readArticleHistory', EMPTY);

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
  }, [setHistory]);

  const removeFromHistory = useCallback((articleId) => {
    setHistory((prev) => prev.filter((entry) => String(entry.id) !== String(articleId)));
  }, [setHistory]);

  const clearHistory = useCallback(() => {
    setHistory([]);
  }, [setHistory]);

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
